#define WIN32_LEAN_AND_MEAN

#include <windows.h>
#include <commctrl.h>
#include <shellapi.h>
#include <shlobj.h>
#include <stdio.h>
#include <wchar.h>
#include "engine.h"

#define APP_TITLE L"VN Revival — No, I’m not a Human"
#define WM_INSTALL_FINISHED (WM_APP + 1)
#define ID_RETRY 1001
#define ID_CHOOSE 1002
#define ID_LAUNCH 1003

static BOOL launchAfterInstall;
static HWND statusLabel;
static HWND progressBar;
static HWND retryButton;
static HWND chooseButton;
static HWND launchButton;
static HWND hintLabel;
static HFONT uiFont;
static HFONT titleFont;
static volatile LONG installationRunning;
static WCHAR applicationDirectory[MAX_PATH * 4];
static WCHAR selectedGamePath[MAX_PATH * 4];
static WCHAR installedGamePath[MAX_PATH * 4];
static WCHAR statusFile[MAX_PATH * 4];
static WCHAR gamePathFile[MAX_PATH * 4];
static void saveChoice(void) {
    HKEY key;if(RegCreateKeyExW(HKEY_CURRENT_USER,L"Software\\VNRevival\\NoHumanLauncher",0,NULL,0,KEY_WRITE,NULL,&key,NULL)==ERROR_SUCCESS){
        RegSetValueExW(key,L"GameFolder",0,REG_SZ,(BYTE*)installedGamePath,(DWORD)((wcslen(installedGamePath)+1)*sizeof(WCHAR)));
        RegCloseKey(key);
    }
}
static void restoreChoice(void) {
    HKEY key;DWORD type,size=sizeof(selectedGamePath);
    if(RegOpenKeyExW(HKEY_CURRENT_USER,L"Software\\VNRevival\\NoHumanLauncher",0,KEY_READ,&key)==ERROR_SUCCESS){
        if(RegQueryValueExW(key,L"GameFolder",NULL,&type,(BYTE*)selectedGamePath,&size)!=ERROR_SUCCESS||type!=REG_SZ)selectedGamePath[0]=0;
        selectedGamePath[_countof(selectedGamePath)-1]=0;
        RegCloseKey(key);
    }
}
static INT_PTR launchInstalledGame(HWND window) {
    WCHAR *steam=wcsstr(installedGamePath,L"\\steamapps\\common\\");
    if(steam){
        WCHAR manifestFolder[MAX_PATH*4],pattern[MAX_PATH*4];size_t length=(size_t)(steam-installedGamePath)+wcslen(L"\\steamapps");
        wcsncpy(manifestFolder,installedGamePath,length);manifestFolder[length]=0;
        swprintf(pattern,_countof(pattern),L"%ls\\appmanifest_*.acf",manifestFolder);WIN32_FIND_DATAW data;HANDLE search=FindFirstFileW(pattern,&data);
        if(search!=INVALID_HANDLE_VALUE){do{
            WCHAR path[MAX_PATH*4],contents[4096];swprintf(path,_countof(path),L"%ls\\%ls",manifestFolder,data.cFileName);
            HANDLE f=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,NULL,OPEN_EXISTING,0,NULL);char bytes[4096];DWORD n=0;
            if(f!=INVALID_HANDLE_VALUE){BOOL read=ReadFile(f,bytes,sizeof(bytes)-1,&n,NULL);CloseHandle(f);bytes[n]=0;if(!read||n==sizeof(bytes)-1)continue;MultiByteToWideChar(CP_UTF8,0,bytes,-1,contents,_countof(contents));
                WCHAR *field=wcsstr(contents,L"\"installdir\"");if(!field)continue;field+=12;while(*field&&(*field==L' '||*field==L'\t'))field++;if(*field++!=L'\"')continue;WCHAR *end=wcschr(field,L'\"');if(!end)continue;*end=0;
                if(!wcscmp(field,wcsrchr(installedGamePath,L'\\')+1)){WCHAR id[32],uri[96];WCHAR *name=data.cFileName+wcslen(L"appmanifest_");size_t i=0;while(name[i]>=L'0'&&name[i]<=L'9'&&i<30){id[i]=name[i];i++;}id[i]=0;if(i&&!wcscmp(name+i,L".acf")){swprintf(uri,_countof(uri),L"steam://rungameid/%ls",id);FindClose(search);return (INT_PTR)ShellExecuteW(window,L"open",uri,NULL,NULL,SW_SHOWNORMAL);}}
            }
        }while(FindNextFileW(search,&data));FindClose(search);}
        return 0;
    }
    WCHAR exe[MAX_PATH*4];swprintf(exe,_countof(exe),L"%ls\\NoImNotAHuman.exe",installedGamePath);
    return (INT_PTR)ShellExecuteW(window,L"open",exe,NULL,installedGamePath,SW_SHOWNORMAL);
}

static void setControlFont(HWND control) {
    SendMessageW(control, WM_SETFONT, (WPARAM)uiFont, TRUE);
}

static void showInstallingState(void) {
    SetWindowTextW(statusLabel, L"Installing all 14 languages…");
    if(hintLabel)SetWindowTextW(hintLabel, L"This may take a few minutes");
    ShowWindow(progressBar, SW_SHOW);
    SendMessageW(progressBar, PBM_SETMARQUEE, TRUE, 35);
    ShowWindow(retryButton, SW_HIDE);
    ShowWindow(chooseButton, SW_HIDE);
    ShowWindow(launchButton, SW_HIDE);
}

static void showFailureState(const WCHAR *message) {
    SetWindowTextW(statusLabel, message && message[0] ? message : L"Installation did not finish. Try again.");
    SendMessageW(progressBar, PBM_SETMARQUEE, FALSE, 0);
    ShowWindow(progressBar, SW_HIDE);
    ShowWindow(retryButton, SW_SHOW);
    ShowWindow(chooseButton, SW_SHOW);
    ShowWindow(launchButton, SW_HIDE);
}

static void showSuccessState(void) {
    SetWindowTextW(statusLabel, L"All translations installed");
    SetWindowTextW(hintLabel, L"Choose your language in the game settings.");
    SendMessageW(progressBar, PBM_SETMARQUEE, FALSE, 0);
    ShowWindow(progressBar, SW_HIDE);
    ShowWindow(retryButton, SW_HIDE);
    ShowWindow(chooseButton, SW_HIDE);
    ShowWindow(launchButton, SW_SHOW);
}

static BOOL readUtf8File(const WCHAR *path, WCHAR *destination, DWORD capacity) {
    HANDLE file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return FALSE;

    char buffer[4096];
    DWORD bytesRead = 0;
    BOOL read = ReadFile(file, buffer, sizeof(buffer) - 1, &bytesRead, NULL);
    CloseHandle(file);
    if (!read || bytesRead == 0) return FALSE;
    buffer[bytesRead] = '\0';

    int converted = MultiByteToWideChar(CP_UTF8, 0, buffer, -1, destination, (int)capacity);
    return converted > 0;
}

static BOOL readStatusMessage(WCHAR *destination, DWORD capacity) {
    return readUtf8File(statusFile, destination, capacity);
}

static void utf8Path(const WCHAR *wide, char *out, int capacity) {
    WideCharToMultiByte(CP_UTF8,0,wide,-1,out,capacity,NULL,NULL);
    for(char *p=out;*p;p++)if(*p=='\\')*p='/';
}
static BOOL gameAt(const WCHAR *path) {
    WCHAR marker[MAX_PATH*4]; swprintf(marker,_countof(marker),L"%ls\\NoImNotAHuman_Data\\boot.config",path);
    return GetFileAttributesW(marker)!=INVALID_FILE_ATTRIBUTES;
}
static DWORD WINAPI installWorker(LPVOID parameter) {
    HWND window=(HWND)parameter; char payload[MAX_PATH*12],game[MAX_PATH*12];
    if(!selectedGamePath[0]) {
        const WCHAR *candidates[]={L"C:\\No, I'm not a Human",L"C:\\Games\\No, I'm not a Human",L"C:\\Program Files (x86)\\Steam\\steamapps\\common\\No, I'm not a Human",L"C:\\GOG Games\\No, I'm not a Human"};
        for(int i=0;i<4;i++)if(gameAt(candidates[i])){wcscpy(selectedGamePath,candidates[i]);break;}
    }
    DWORD result=2;
    if(selectedGamePath[0]) {
        utf8Path(applicationDirectory,payload,sizeof(payload));strcat(payload,"/Resources/Payload");
        utf8Path(selectedGamePath,game,sizeof(game));
        if(nh_install(payload,game,"all")){
            wcscpy(installedGamePath,selectedGamePath);result=0;
        }else{
            FILE *f=_wfopen(statusFile,L"wb");if(f){fputs(nh_error(),f);fclose(f);}result=1;
        }
    }
    InterlockedExchange(&installationRunning,0);
    PostMessageW(window,WM_INSTALL_FINISHED,(WPARAM)result,0);return 0;
}

static void startInstallation(HWND window) {
    if (InterlockedCompareExchange(&installationRunning, 1, 0) != 0) return;
    showInstallingState();
    HANDLE thread = CreateThread(NULL, 0, installWorker, window, 0, NULL);
    if (!thread) {
        InterlockedExchange(&installationRunning, 0);
        showFailureState(L"The installer worker could not be started.");
        return;
    }
    CloseHandle(thread);
}

static BOOL chooseGameFolder(HWND owner) {
    BROWSEINFOW browse = {0};
    browse.hwndOwner = owner;
    browse.lpszTitle = L"Choose the No, I’m not a Human folder";
    browse.ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE;
    PIDLIST_ABSOLUTE item = SHBrowseForFolderW(&browse);
    if (!item) return FALSE;
    BOOL resolved = SHGetPathFromIDListW(item, selectedGamePath);
    CoTaskMemFree(item);
    return resolved;
}

static void doLaunch(HWND window) {
                    if (installedGamePath[0]) {
                        if(!nh_prepare_launch()) {
                            WCHAR details[2048];MultiByteToWideChar(CP_UTF8,0,nh_error(),-1,details,_countof(details));showFailureState(details);
                        }else if(launchInstalledGame(window)<=32){
                            showFailureState(L"The game could not be launched.");
                        }else{DestroyWindow(window);}
                    } else {
                        showFailureState(L"The game path is unavailable. Retry the installation.");
                    }
}

static LRESULT CALLBACK windowProcedure(HWND window, UINT message, WPARAM wParam, LPARAM lParam) {
    (void)lParam;
    switch (message) {
        case WM_CREATE: {
            uiFont = CreateFontW(-18, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
                OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Segoe UI");
            HWND title = CreateWindowW(L"STATIC", APP_TITLE, WS_CHILD | WS_VISIBLE,
                36, 30, 520, 36, window, NULL, NULL, NULL);
            titleFont = CreateFontW(-25, 0, 0, 0, FW_SEMIBOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
                OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Segoe UI");
            SendMessageW(title, WM_SETFONT, (WPARAM)titleFont, TRUE);

            statusLabel = CreateWindowW(L"STATIC", L"Preparing installation…", WS_CHILD | WS_VISIBLE,
                38, 88, 500, 58, window, NULL, NULL, NULL);
            progressBar = CreateWindowW(PROGRESS_CLASSW, NULL, WS_CHILD | WS_VISIBLE | PBS_MARQUEE,
                38, 151, 500, 12, window, NULL, NULL, NULL);
            retryButton = CreateWindowW(L"BUTTON", L"Retry", WS_CHILD | BS_PUSHBUTTON,
                38, 185, 132, 38, window, (HMENU)ID_RETRY, NULL, NULL);
            chooseButton = CreateWindowW(L"BUTTON", L"Choose game…", WS_CHILD | BS_PUSHBUTTON,
                182, 185, 160, 38, window, (HMENU)ID_CHOOSE, NULL, NULL);
            launchButton = CreateWindowW(L"BUTTON", L"Launch game", WS_CHILD | BS_DEFPUSHBUTTON,
                38, 185, 180, 40, window, (HMENU)ID_LAUNCH, NULL, NULL);
            hintLabel = CreateWindowW(L"STATIC", L"This may take a few minutes", WS_CHILD | WS_VISIBLE,
                38, 236, 500, 26, window, NULL, NULL, NULL);

            setControlFont(statusLabel);
            setControlFont(retryButton);
            setControlFont(chooseButton);
            setControlFont(launchButton);
            setControlFont(hintLabel);
            PostMessageW(window, WM_APP, 0, 0);
            return 0;
        }
        case WM_APP:
            startInstallation(window);
            return 0;
        case WM_INSTALL_FINISHED: {
            DWORD exitCode = (DWORD)wParam;
            if (exitCode == 0) {
                saveChoice();
                showSuccessState();
                if(launchAfterInstall)doLaunch(window);
            } else {
                WCHAR details[2048] = {0};
                if (!readStatusMessage(details, _countof(details)) && exitCode == 2) {
                    wcscpy(details, L"No, I’m not a Human was not found. Choose the game folder.");
                }
                showFailureState(details);
            }
            return 0;
        }
        case WM_COMMAND:
            switch (LOWORD(wParam)) {
                case ID_RETRY:
                    startInstallation(window);
                    return 0;
                case ID_CHOOSE:
                    if (chooseGameFolder(window)) startInstallation(window);
                    return 0;
                case ID_LAUNCH:
                    doLaunch(window);
                    return 0;
            }
            break;
        case WM_CLOSE:
            if (InterlockedCompareExchange(&installationRunning, 0, 0) != 0) {
                MessageBoxW(window, L"Installation is still in progress.", APP_TITLE, MB_OK | MB_ICONINFORMATION);
                return 0;
            }
            DestroyWindow(window);
            return 0;
        case WM_DESTROY:
            if (uiFont) DeleteObject(uiFont);
            if (titleFont) DeleteObject(titleFont);
            DeleteFileW(statusFile);
            DeleteFileW(gamePathFile);
            PostQuitMessage(0);
            return 0;
    }
    return DefWindowProcW(window, message, wParam, lParam);
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR commandLine, int showCommand) {
    (void)previous;
    restoreChoice();
    int argc=0;LPWSTR *args=CommandLineToArgvW(GetCommandLineW(),&argc);
    for(int i=1;i<argc;i++){
        if(!wcscmp(args[i],L"--launch")){launchAfterInstall=TRUE;}
        else if(!wcscmp(args[i],L"--game")&&i+1<argc){wcsncpy(selectedGamePath,args[++i],_countof(selectedGamePath)-1);}
    }
    if(args)LocalFree(args);
    (void)commandLine;

    INITCOMMONCONTROLSEX controls = {sizeof(controls), ICC_PROGRESS_CLASS};
    InitCommonControlsEx(&controls);
    CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);

    WCHAR executablePath[MAX_PATH * 4];
    DWORD length = GetModuleFileNameW(NULL, executablePath, _countof(executablePath));
    if (length == 0 || length >= _countof(executablePath)) return 1;
    WCHAR *separator = wcsrchr(executablePath, L'\\');
    if (!separator) return 1;
    *separator = L'\0';
    wcscpy(applicationDirectory, executablePath);

    WCHAR temporaryDirectory[MAX_PATH * 2];
    GetTempPathW(_countof(temporaryDirectory), temporaryDirectory);
    swprintf(statusFile, _countof(statusFile), L"%lsVNRevival-NoHuman-Installer-%lu.txt", temporaryDirectory, GetCurrentProcessId());
    swprintf(gamePathFile, _countof(gamePathFile), L"%lsVNRevival-NoHuman-GamePath-%lu.txt", temporaryDirectory, GetCurrentProcessId());

    WNDCLASSEXW windowClass = {0};
    windowClass.cbSize = sizeof(windowClass);
    windowClass.lpfnWndProc = windowProcedure;
    windowClass.hInstance = instance;
    windowClass.hIcon = LoadIconW(instance, MAKEINTRESOURCEW(1));
    windowClass.hIconSm = windowClass.hIcon;
    windowClass.hCursor = LoadCursorW(NULL, IDC_ARROW);
    windowClass.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    windowClass.lpszClassName = L"VNRevivalNoHumanInstallerWindow";
    if (!RegisterClassExW(&windowClass)) return 1;

    // Controls use client coordinates. Include the actual caption and border
    // metrics instead of subtracting a fixed non-client height at high DPI.
    const DWORD windowStyle = WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX;
    RECT windowBounds = {0, 0, 590, 290};
    if (!AdjustWindowRectEx(&windowBounds, windowStyle, FALSE, 0)) return 1;
    const int width = windowBounds.right - windowBounds.left;
    const int height = windowBounds.bottom - windowBounds.top;
    RECT desktop;
    SystemParametersInfoW(SPI_GETWORKAREA, 0, &desktop, 0);
    int x = desktop.left + (desktop.right - desktop.left - width) / 2;
    int y = desktop.top + (desktop.bottom - desktop.top - height) / 2;
    HWND window = CreateWindowExW(
        0,
        windowClass.lpszClassName,
        APP_TITLE,
        windowStyle,
        x,
        y,
        width,
        height,
        NULL,
        NULL,
        instance,
        NULL
    );
    if (!window) return 1;

    ShowWindow(window, showCommand);
    UpdateWindow(window);
    MSG message;
    while (GetMessageW(&message, NULL, 0, 0) > 0) {
        TranslateMessage(&message);
        DispatchMessageW(&message);
    }
    CoUninitialize();
    return (int)message.wParam;
}
