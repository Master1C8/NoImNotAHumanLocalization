/* Game-specific adapter for the Stardew installer UI and replacement contract.
 * Frozen profiles; bounded decoding, source pins, ownership and recovery journal.
 */
#include "engine.h"
#include "payload_pin.h"
#include "vendor/zstd/zstd.h"
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <sys/stat.h>
#ifdef _WIN32
#include <windows.h>
#include <bcrypt.h>
#include <tlhelp32.h>
#include <direct.h>
#else
#include <CommonCrypto/CommonDigest.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/file.h>
#endif

#define CAP 4096
#define MAX_FILES 512
static char error_text[CAP];
const char *nh_error(void) { return error_text; }
static int fail(const char *message,const char *path) { snprintf(error_text,CAP,"%s: %s",message,path?path:""); return 0; }
static int join(char *out,const char *a,const char *b) { return snprintf(out,CAP,"%s/%s",a,b)>0 && strlen(a)+strlen(b)+2<CAP; }
static int safe(const char *p) {
    if(!p || !*p || *p=='/' || strchr(p,'\\') || strchr(p,':'))return 0;
    for(const char *s=p;*s;s++)if((unsigned char)*s<32)return 0;
    const char *s=p; do { const char *e=strchr(s,'/'); size_t n=e?(size_t)(e-s):strlen(s); if(!n || (n==1 && s[0]=='.') || (n==2 && s[0]=='.' && s[1]=='.'))return 0; s=e?e+1:NULL; }while(s);
    return 1;
}
#ifdef _WIN32
static wchar_t *wide(const char *s) { int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s,-1,NULL,0); if(!n)return NULL; wchar_t *w=calloc(n,sizeof(wchar_t)); if(w)MultiByteToWideChar(CP_UTF8,0,s,-1,w,n); return w; }
static FILE *openfile(const char *p,const char *mode) { wchar_t *w=wide(p),*m=wide(mode); FILE *f=w&&m?_wfopen(w,m):NULL; free(w);free(m);return f; }
static int makedir(const char *p) { wchar_t *w=wide(p); int r=w?_wmkdir(w):-1;free(w);return r==0||errno==EEXIST; }
static int movefile(const char *a,const char *b) { wchar_t *x=wide(a),*y=wide(b); int r=x&&y&&MoveFileExW(x,y,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH);free(x);free(y);return r; }
static int removefile(const char *p) { wchar_t *w=wide(p); int r=w&&DeleteFileW(w);free(w);return r; }
static int exists(const char *p) { wchar_t *w=wide(p); DWORD a=w?GetFileAttributesW(w):INVALID_FILE_ATTRIBUTES;free(w);return a!=INVALID_FILE_ATTRIBUTES; }
static int linkpath(const char *p) { wchar_t *w=wide(p);DWORD a=w?GetFileAttributesW(w):INVALID_FILE_ATTRIBUTES;free(w);return a!=INVALID_FILE_ATTRIBUTES && (a&FILE_ATTRIBUTE_REPARSE_POINT); }
#else
static FILE *openfile(const char *p,const char *m) {return fopen(p,m);}
static int makedir(const char *p) {return mkdir(p,0700)==0||errno==EEXIST;}
static int movefile(const char *a,const char *b) {return rename(a,b)==0;}
static int removefile(const char *p) {return unlink(p)==0;}
static int exists(const char *p) {struct stat s;return lstat(p,&s)==0;}
static int linkpath(const char *p) {struct stat s;return lstat(p,&s)==0&&S_ISLNK(s.st_mode);}
#endif
static int parents(const char *p) {char s[CAP]; if(strlen(p)>=CAP)return 0; strcpy(s,p);for(char *q=s+1;*q;q++)if(*q=='/'){*q=0;if(linkpath(s)||!makedir(s))return 0;*q='/';}return !linkpath(s);}
static int confined(const char *root,const char *rel,char out[CAP]) {if(!safe(rel)||!join(out,root,rel))return 0;char p[CAP];strcpy(p,out);for(char *q=p+strlen(root);;q++){if(*q=='/'||!*q){char c=*q;*q=0;if(linkpath(p))return 0;*q=c;if(!c)break;}}return 1;}
static char *line(FILE *f) {size_t n=0,c=1024;char *s=malloc(c);if(!s)return NULL;int x;while((x=fgetc(f))!=EOF && x!='\n'){if(n+1>=c){c*=2;if(c>1024*1024){free(s);return NULL;}char *t=realloc(s,c);if(!t){free(s);return NULL;}s=t;}s[n++]=(char)x;}if(!n&&x==EOF){free(s);return NULL;}s[n]=0;return s;}
static int fields(char *s,char **v,int n) {for(int i=0;i<n;i++){v[i]=s;if(i<n-1){char *p=strchr(s,'\t');if(!p)return 0;*p=0;s=p+1;}}return strchr(v[n-1],'\t')==NULL;}
static int hexhash(const char *s) {if(strlen(s)!=64)return 0;for(int i=0;i<64;i++)if(!((s[i]>='0'&&s[i]<='9')||(s[i]>='a'&&s[i]<='f')))return 0;return 1;}
static int hashfile(const char *p,char out[65]) {
    FILE *f=openfile(p,"rb");if(!f)return 0;unsigned char b[65536],digest[32];size_t n;
#ifdef _WIN32
    BCRYPT_ALG_HANDLE a=NULL;BCRYPT_HASH_HANDLE h=NULL;DWORD len=0,got=0;unsigned char *object=NULL;
    if(BCryptOpenAlgorithmProvider(&a,BCRYPT_SHA256_ALGORITHM,NULL,0)<0||BCryptGetProperty(a,BCRYPT_OBJECT_LENGTH,(PUCHAR)&len,sizeof(len),&got,0)<0){fclose(f);if(a)BCryptCloseAlgorithmProvider(a,0);return 0;}
    object=malloc(len);if(!object||BCryptCreateHash(a,&h,object,len,NULL,0,0)<0){free(object);fclose(f);BCryptCloseAlgorithmProvider(a,0);return 0;}
    int ok=1;while((n=fread(b,1,sizeof(b),f)))if(BCryptHashData(h,b,(ULONG)n,0)<0)ok=0;
    ok=ok&&!ferror(f)&&BCryptFinishHash(h,digest,32,0)>=0;BCryptDestroyHash(h);BCryptCloseAlgorithmProvider(a,0);free(object);fclose(f);if(!ok)return 0;
#else
    CC_SHA256_CTX h;CC_SHA256_Init(&h);while((n=fread(b,1,sizeof(b),f)))CC_SHA256_Update(&h,b,(CC_LONG)n);int ok=!ferror(f);fclose(f);if(!ok)return 0;CC_SHA256_Final(digest,&h);
#endif
    for(int i=0;i<32;i++)snprintf(out+i*2,3,"%02x",digest[i]);out[64]=0;return 1;
}
static int copyfile(const char *a,const char *b) {if(!parents(b))return 0;FILE *i=openfile(a,"rb"),*o=openfile(b,"wb");if(!i||!o){if(i)fclose(i);if(o)fclose(o);return 0;}char data[65536];size_t n;int ok=1;while((n=fread(data,1,sizeof(data),i)))if(fwrite(data,1,n,o)!=n){ok=0;break;}ok=ok&&!ferror(i);fclose(i);if(fclose(o))ok=0;return ok;}
static int puttext(const char *p,const char *s) {if(!parents(p))return 0;char t[CAP];snprintf(t,CAP,"%s.new",p);if(exists(t))return 0;FILE *f=openfile(t,"wb");if(!f)return 0;int ok=fwrite(s,1,strlen(s),f)==strlen(s);if(fclose(f))ok=0;return ok&&movefile(t,p);}
static int equals(const char *p,const char *expected) {char h[65];return hashfile(p,h)&&!strcmp(h,expected);}
static int locale_ok(const char *s) {return s && !strcmp(s,"all");}
typedef struct {char *path,*base,*sha,*refs;uint64_t size;} Item;
static int loaditems(const char *p,Item *items,int *count) {FILE *f=openfile(p,"rb");if(!f)return 0;char *s;*count=0;while((s=line(f))){char *v[5];if(*count>=MAX_FILES||!fields(s,v,5)||!safe(v[0])||(!hexhash(v[1])&&strcmp(v[1],"-"))||!hexhash(v[2])){free(s);fclose(f);return 0;}Item *r=&items[(*count)++];r->path=v[0];r->base=v[1];r->sha=v[2];r->size=strtoull(v[3],NULL,10);r->refs=v[4];if(r->size>512*1024*1024){fclose(f);return 0;}for(int i=0;i<*count-1;i++)if(!strcmp(items[i].path,r->path)){fclose(f);return 0;}}fclose(f);return *count>0;}
static void freeitems(Item *a,int n){for(int i=0;i<n;i++)free(a[i].path);}
typedef struct {char sha[65];char *base;uint64_t offset;size_t packed,raw;} Blob;
static void freeblobs(Blob *b,size_t n){for(size_t i=0;i<n;i++)free(b[i].base);free(b);}
static int verify_payload(const char *payload) {char path[CAP];join(path,payload,"inventory.tsv");if(!equals(path,NH_INVENTORY_SHA))return fail("Payload inventory differs from this application",path);FILE *f=openfile(path,"rb");if(!f)return fail("Missing payload inventory",path);char *s;int n=0;while((s=line(f))){char *v[2],p[CAP];int ok=fields(s,v,2)&&hexhash(v[1])&&confined(payload,v[0],p)&&equals(p,v[1]);if(!ok){free(s);fclose(f);return fail("Payload verification failed",path);}n++;free(s);}fclose(f);return n>=6?1:fail("Incomplete payload",payload);}
static int running(const char *game) {
#ifdef _WIN32
    HANDLE snap=CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);if(snap==INVALID_HANDLE_VALUE)return 1;PROCESSENTRY32W p={0};p.dwSize=sizeof(p);int found=0;
    if(Process32FirstW(snap,&p))do{if(!_wcsicmp(p.szExeFile,L"NoImNotAHuman.exe")){found=1;break;}}while(Process32NextW(snap,&p));CloseHandle(snap);return found;
#else
    (void)game;FILE *f=popen("/bin/ps -axo command", "r");if(!f)return 1;char *s;int found=0;while((s=line(f))){if(strstr(s,"NoImNotAHuman.exe"))found=1;free(s);}if(pclose(f)!=0)return 1;return found;
#endif
}
static int rollback(const char *game,const char *cache) {
    char jp[CAP];join(jp,cache,"transaction.tsv");if(!exists(jp))return 1;
    FILE *f=openfile(jp,"rb");if(!f)return fail("Cannot read recovery journal",jp);char *s;int ok=1;
    while((s=line(f))){char *v[3],target[CAP],backup[CAP],rel[CAP];if(!fields(s,v,3)||!confined(game,v[0],target)||!hexhash(v[2])||(!hexhash(v[1])&&strcmp(v[1],"-"))){ok=0;free(s);break;}
        if(exists(target)&&!equals(target,v[2])&&(strcmp(v[1],"-")==0||!equals(target,v[1]))){fail("Recovery refuses externally changed file",target);ok=0;free(s);break;}
        if(strcmp(v[1],"-")){char restore[CAP];snprintf(rel,CAP,"before/%s",v[0]);snprintf(restore,CAP,"%s.recover",target);if(!confined(cache,rel,backup)||!equals(backup,v[1])||!copyfile(backup,restore)||!equals(restore,v[1])||!movefile(restore,target)||!equals(target,v[1]))ok=0;}
        else if(exists(target)&&!removefile(target))ok=0;
        free(s);if(!ok)break;
    }fclose(f);
    if(ok){char previous[CAP],active[CAP];join(previous,cache,"active.before");join(active,cache,"active.txt");FILE *p=openfile(previous,"rb");char *old=p?line(p):NULL;if(p)fclose(p);if(!old)ok=0;else if(!strcmp(old,"-")){if(exists(active))ok=removefile(active);}else if(locale_ok(old)){char tmp[CAP];snprintf(tmp,CAP,"%s.new",active);if(exists(tmp))removefile(tmp);char value[32];snprintf(value,sizeof(value),"%s\n",old);ok=puttext(active,value);}else ok=0;free(old);}
    if(ok)ok=removefile(jp);return ok?1:fail("Installation recovery incomplete; files retained",jp);
}
static int decode(Item *item,const char *payload,const char *cache,Blob *blobs,size_t count,const char *output) {
    if(!parents(output))return 0;FILE *o=openfile(output,"wb");if(!o)return 0;char packedpath[CAP];join(packedpath,payload,"chunks.bin");FILE *pack=openfile(packedpath,"rb");if(!pack){fclose(o);return 0;}
    const char *s=item->refs;uint64_t total=0;unsigned char *in=malloc(270336),*out=malloc(262144);if(!in||!out){free(in);free(out);fclose(o);fclose(pack);return 0;}int ok=1;
    while(*s){char *e;unsigned long idx=strtoul(s,&e,10);if(e==s||(*e&&*e!=',')||idx>=count){ok=0;break;}Blob *b=&blobs[idx];if(b->raw>262144||b->packed>270336){ok=0;break;}
        if(b->packed){if(fseek(pack,(long)b->offset,SEEK_SET)||fread(in,1,b->packed,pack)!=b->packed||ZSTD_decompress(out,b->raw,in,b->packed)!=b->raw){ok=0;break;}}
        else{char rel[CAP],path[CAP];snprintf(rel,CAP,"originals/%s",b->base);if(!confined(cache,rel,path)){ok=0;break;}FILE *f=openfile(path,"rb");if(!f){ok=0;break;}ok=!fseek(f,(long)b->offset,SEEK_SET)&&fread(out,1,b->raw,f)==b->raw;fclose(f);if(!ok)break;}
        if(fwrite(out,1,b->raw,o)!=b->raw){ok=0;break;}total+=b->raw;if(total>item->size){ok=0;break;}s=*e?e+1:e;
    }fclose(pack);free(in);free(out);if(fclose(o))ok=0;return ok&&total==item->size&&equals(output,item->sha);
}
static int install_inner(const char *payload,const char *game,const char *locale,const char *cache) {
    if(!locale_ok(locale))return fail("Unknown language",locale);
    char path[CAP];if(!confined(game,"NoImNotAHuman_Data/boot.config",path))return fail("Unsafe game folder",game);FILE *boot=openfile(path,"rb");if(!boot)return fail("Game not found",game);char bootdata[4096]={0};fread(bootdata,1,4095,boot);fclose(boot);if(!strstr(bootdata,"build-guid=c003ddc7de634775a85305fef3b9a0d3"))return fail("Unsupported game build; expected 1.3.19",game);
    if(running(game))return fail("Close No, I'm not a Human before installation",game);
    if(!verify_payload(payload)||!rollback(game,cache))return 0;
#ifdef NOHUMAN_TESTING
    if(getenv("NOHUMAN_RECOVER_ONLY"))return 1;
#endif
    // Retain original source files independently of each replacement transaction.
    join(path,payload,"originals.tsv");FILE *f=openfile(path,"rb");if(!f)return fail("Original input list missing",path);char *s;
    while((s=line(f))){char *v[2],src[CAP],dst[CAP],rel[CAP];int ok=fields(s,v,2)&&hexhash(v[1])&&confined(game,v[0],src);snprintf(rel,CAP,"originals/%s",v[0]);ok=ok&&confined(cache,rel,dst);
        if(ok&&!exists(dst))ok=equals(src,v[1])&&copyfile(src,dst);ok=ok&&equals(dst,v[1]);free(s);if(!ok){fclose(f);return fail("Original game resources differ; refusing replacement",game);}}
    fclose(f);
    // Install the complete immutable language set into the game-owned cache.
    join(path,payload,"inventory.tsv");f=openfile(path,"rb");if(!f)return 0;
    while((s=line(f))){char *v[2],src[CAP],dst[CAP],rel[CAP];int ok=fields(s,v,2)&&confined(payload,v[0],src);snprintf(rel,CAP,"payload/%s/%s",NH_INVENTORY_SHA,v[0]);ok=ok&&confined(cache,rel,dst);if(ok&&!exists(dst))ok=copyfile(src,dst);ok=ok&&equals(dst,v[1]);free(s);if(!ok){fclose(f);return fail("Owned cache differs; refusing overwrite",cache);}}fclose(f);
    Blob *blobs=NULL;size_t count=0,capacity=0;join(path,payload,"blobs.tsv");f=openfile(path,"rb");if(!f)return 0;
    while((s=line(f))){char *v[5];if(!fields(s,v,5)||!hexhash(v[0])||count>=100000){free(s);fclose(f);freeblobs(blobs,count);return fail("Invalid chunk index",path);}if(count==capacity){capacity=capacity?capacity*2:1024;Blob *next=realloc(blobs,capacity*sizeof(Blob));if(!next){free(s);fclose(f);freeblobs(blobs,count);return 0;}blobs=next;}Blob *b=&blobs[count++];b->base=NULL;strcpy(b->sha,v[0]);b->offset=strtoull(v[1],NULL,10);b->packed=(size_t)strtoull(v[2],NULL,10);b->raw=(size_t)strtoull(v[3],NULL,10);if(strlen(v[4])>=CAP){free(s);fclose(f);freeblobs(blobs,count);return 0;}b->base=strdup(v[4]);if(!b->base){free(s);fclose(f);freeblobs(blobs,count);return 0;}free(s);}fclose(f);
    Item items[MAX_FILES]={0},old[MAX_FILES]={0};int n=0,on=0;char rel[CAP];snprintf(rel,CAP,"profiles/%s.tsv",locale);join(path,payload,rel);if(!loaditems(path,items,&n)){freeblobs(blobs,count);return fail("Invalid language profile",path);}
    join(path,cache,"active.txt");f=openfile(path,"rb");if(f){s=line(f);fclose(f);if(!s||!locale_ok(s)){free(s);freeblobs(blobs,count);freeitems(items,n);return fail("Invalid prior installation receipt",path);}snprintf(rel,CAP,"profiles/%s.tsv",s);free(s);join(path,payload,rel);if(!loaditems(path,old,&on)){freeblobs(blobs,count);freeitems(items,n);return fail("Prior profile missing",path);}}
    char previouspath[CAP],activepath[CAP],previousvalue[32]="-\n";join(previouspath,cache,"active.before");join(activepath,cache,"active.txt");f=openfile(activepath,"rb");if(f){s=line(f);fclose(f);if(s){snprintf(previousvalue,sizeof(previousvalue),"%s\n",s);free(s);}}char prevtemp[CAP];snprintf(prevtemp,CAP,"%s.new",previouspath);if(exists(prevtemp))removefile(prevtemp);if(!puttext(previouspath,previousvalue)){freeblobs(blobs,count);freeitems(items,n);freeitems(old,on);return fail("Cannot save recovery receipt",previouspath);}
    FILE *journal=NULL;char journalpath[CAP],tempjournal[CAP];join(journalpath,cache,"transaction.tsv");join(tempjournal,cache,"transaction.new");if(exists(tempjournal))removefile(tempjournal);journal=openfile(tempjournal,"wb");int ok=journal!=NULL;
    for(int i=0;i<n&&ok;i++){Item *r=&items[i];char target[CAP],before[65]="-",stage[CAP],backup[CAP];ok=confined(game,r->path,target);if(!ok)break;
        if(exists(target)){ok=hashfile(target,before);int owned=0;for(int j=0;j<on;j++)if(!strcmp(old[j].path,r->path)&&!strcmp(before,old[j].sha))owned=1;
            // BepInEx legitimately expands its own generated config after startup.
            if(on&&!strcmp(r->path,"BepInEx/config/BepInEx.cfg"))continue;
            ok=ok&&(!strcmp(before,r->base)||owned||!strcmp(before,r->sha));
        }else ok=!strcmp(r->base,"-");
        if(!ok){fail("Unknown modification; original and other mods are protected",r->path);break;}
        snprintf(rel,CAP,"stage/%s",r->path);ok=confined(cache,rel,stage)&&decode(r,payload,cache,blobs,count,stage);
        if(!ok){fail("Profile reconstruction failed",r->path);break;}
        if(strcmp(before,"-")){snprintf(rel,CAP,"before/%s",r->path);ok=confined(cache,rel,backup)&&copyfile(target,backup)&&equals(backup,before);}
        if(ok)ok=fprintf(journal,"%s\t%s\t%s\n",r->path,before,r->sha)>0;
    }
    if(journal&&fclose(journal))ok=0;
    if(ok)ok=movefile(tempjournal,journalpath);else removefile(tempjournal);
    if(ok){f=openfile(journalpath,"rb");int applied=0;while(f&&(s=line(f))){char *v[3],target[CAP],stage[CAP];ok=fields(s,v,3)&&confined(game,v[0],target);snprintf(rel,CAP,"stage/%s",v[0]);ok=ok&&confined(cache,rel,stage);
            ok=ok&&((!strcmp(v[1],"-")&&!exists(target))||equals(target,v[1]))&&parents(target)&&movefile(stage,target)&&equals(target,v[2]);free(s);applied++;
#ifdef NOHUMAN_TESTING
            const char *inject=getenv("NOHUMAN_FAIL_AFTER");if(inject&&atoi(inject)==applied){ok=0;fail("Injected interruption",game);}
            const char *crash=getenv("NOHUMAN_CRASH_AFTER");if(crash&&atoi(crash)==applied){
#ifdef _WIN32
                ExitProcess(75);
#else
                _exit(75);
#endif
            }
#endif
            if(!ok)break;}
        if(f)fclose(f);else ok=0;
    }
    if(!ok&&exists(journalpath))rollback(game,cache);
    if(ok){join(path,cache,"active.txt");char active[32];snprintf(active,sizeof(active),"%s\n",locale);ok=puttext(path,active);if(ok)ok=removefile(journalpath);else rollback(game,cache);}
    freeblobs(blobs,count);freeitems(items,n);freeitems(old,on);if(!ok&&!error_text[0])fail("Installation failed",game);return ok;
}
int nh_install(const char *payload,const char *game,const char *locale) {
    error_text[0]=0;char cache[CAP],owner[CAP],bootpath[CAP];
    if(!locale_ok(locale))return fail("Unknown language",locale);
    if(!confined(game,"NoImNotAHuman_Data/boot.config",bootpath))return fail("Unsafe game folder",game);FILE *boot=openfile(bootpath,"rb");char version[4096]={0};if(boot){fread(version,1,4095,boot);fclose(boot);}if(!strstr(version,"build-guid=c003ddc7de634775a85305fef3b9a0d3"))return fail("Unsupported game build; expected 1.3.19",game);
    if(running(game))return fail("Close No, I'm not a Human before installation",game);
    if(!verify_payload(payload))return 0;
    char versionlist[CAP];join(versionlist,payload,"game-version.tsv");FILE *versions=openfile(versionlist,"rb");if(!versions)return fail("Missing game code version pins",payload);char *record;int versioncount=0;
    while((record=line(versions))){char *v[2],source[CAP];int ok=fields(record,v,2)&&hexhash(v[1])&&confined(game,v[0],source)&&equals(source,v[1]);free(record);if(!ok){fclose(versions);return fail("Game code or metadata differs from the verified build",game);}versioncount++;}fclose(versions);if(versioncount!=2)return fail("Incomplete game code version pins",payload);
    if(!confined(game,"VNRevival-NoHuman",cache))return fail("Unsafe cache path",game);join(owner,cache,"owner.txt");const char *identity="fun.vnrevival.nohuman.launcher/0.2.0\n";
    if(exists(cache)){FILE *f=openfile(owner,"rb");char data[128]={0};if(f){fread(data,1,127,f);fclose(f);}if(strcmp(data,identity))return fail("Existing folder belongs to another application",cache);}
    else if(!makedir(cache)||!puttext(owner,identity))return fail("Cannot create owned installation directory",cache);
    char lockpath[CAP];join(lockpath,cache,"install.lock");int result;
#ifdef _WIN32
    wchar_t *w=wide(lockpath);HANDLE lock=CreateFileW(w,GENERIC_READ|GENERIC_WRITE,0,NULL,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);free(w);if(lock==INVALID_HANDLE_VALUE)return fail("Another installer is running",game);result=install_inner(payload,game,locale,cache);CloseHandle(lock);
#else
    int lock=open(lockpath,O_CREAT|O_RDWR,0600);if(lock<0||flock(lock,LOCK_EX|LOCK_NB)){if(lock>=0)close(lock);return fail("Another installer is running",game);}result=install_inner(payload,game,locale,cache);close(lock);
#endif
    return result;
}
int nh_prepare_launch(void) {
    const char *locale="all";
#ifdef _WIN32
    if(!locale_ok(locale))return fail("Unknown language",locale);
    // Locale selection and persistence stay inside the game.
    // Wine additionally needs an application-specific proxy DLL override.
    if(GetProcAddress(GetModuleHandleW(L"ntdll.dll"),"wine_get_version")){
        HKEY key;DWORD type=0,size=128;wchar_t current[64]={0};
        if(RegCreateKeyExW(HKEY_CURRENT_USER,L"Software\\Wine\\AppDefaults\\NoImNotAHuman.exe\\DllOverrides",0,NULL,0,KEY_READ|KEY_WRITE,NULL,&key,NULL)!=ERROR_SUCCESS)return fail("Cannot configure game loader",locale);
        LONG r=RegQueryValueExW(key,L"winhttp",NULL,&type,(BYTE*)current,&size);
        if(r!=ERROR_FILE_NOT_FOUND&&(r!=ERROR_SUCCESS||type!=REG_SZ||(wcscmp(current,L"native,builtin")&&wcscmp(current,L"native, builtin")))){RegCloseKey(key);return fail("Preserve the existing winhttp override",locale);}
        int ok=RegSetValueExW(key,L"winhttp",0,REG_SZ,(BYTE*)L"native,builtin",sizeof(L"native,builtin"))==ERROR_SUCCESS;RegCloseKey(key);return ok?1:fail("Cannot configure game loader",locale);
    }
    return 1;
#else
    (void)locale;return 1; /* The native UI changes the selected wrapper's registry. */
#endif
}
#ifdef NOHUMAN_CLI
int main(int argc,char **argv){if(argc!=4){fprintf(stderr,"Usage: nohuman-engine <payload> <game> <locale>\n");return 2;}if(!nh_install(argv[1],argv[2],argv[3])){fprintf(stderr,"%s\n",nh_error());return 1;}puts("All 14 language profiles installed; selected profile verified.");return 0;}
#endif
