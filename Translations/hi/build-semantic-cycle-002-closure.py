#!/usr/bin/env python3
"""Rebuild/verify Hindi cycle-002 closure, technical context, and exact review delta."""
import argparse,collections,hashlib,importlib.util,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HI=ROOT/"Translations/hi"
OUT=HI/"semantic-cycle-002-closure.json"
CONTEXT=HI/"semantic-cycle-002-runtime-context.json"
DELTA=HI/"semantic-cycle-002-review-delta.json"
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def ih(ids):return hashlib.sha256(("\n".join(ids)+"\n").encode()).hexdigest()
def j(path):return json.loads(Path(path).read_text(encoding="utf-8"))
def source_rows(path):return [json.loads(x) for x in Path(path).read_text().splitlines()]
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def helper():
 path=HI/"build-semantic-cycle-001-closure.py"
 spec=importlib.util.spec_from_file_location("cycle001_helper",path)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module
def runtime_nodes(fields):
 blob=bytes(j(ROOT/"Source/glossary-corpus-v2/runtime-bindings.json")["sharedassets0.assets:2743"]["compiledYarnProgram"])
 nodes={}
 for n,w,v in fields(blob):
  if (n,w)!=(2,2):continue
  parts=list(fields(v))
  if len(parts)<2 or parts[0][:2]!=(1,2):continue
  name=parts[0][2].decode();ins=[]
  for q,qw,raw in fields(parts[1][2]):
   if (q,qw)!=(2,2):continue
   opcode=None;strings=[]
   for a,b,data in fields(raw):
    if (a,b)==(1,0):opcode=data
    elif (a,b)==(2,2):
     for aa,bb,operand in fields(data):
      if (aa,bb)==(1,2):strings.append(operand.decode("utf-8"))
   ins.append({"index":len(ins),"opcode":opcode,"strings":strings})
  nodes[name]=ins
 return nodes
def build():
 a=j(HI/"semantic-cycle-002-adjudication.json")
 gate=j(HI/"semantic-cycle-002-structural-gate.json")
 old=j(HI/"semantic-cycle-001-closure.json")
 review=j(HI/"independent-review-01/consolidated-full-unit-findings.json")
 assert len(a["items"])==21 and gate["acceptedIds"]==16538
 assert not any(gate[k] for k in ("duplicateIds","missingIds","extraIds","exactSpanFailures"))
 assert sha(ROOT/"Source/localization-inventory-v3/strings.jsonl")==a["sourceInventorySha256"]
 assert sha(ROOT/"Source/localization-inventory-v3/static-text.jsonl")==a["staticInventorySha256"]
 assert sha(ROOT/"Documentation/glossary-translations/hi/layer.json")==a["glossaryLayerSha256"]
 assert sha(ROOT/"Source/glossary-corpus-v2/runtime-bindings.json")==a["compiledRuntimeBindingsSha256"]
 assert sha(HI/"semantic-cycle-001-closure.json")==a["previousClosureSha256"]
 assert sha(HI/"independent-review-01/consolidated-full-unit-findings.json")==a["independentReviewFindingsSha256"]
 for f in gate["files"]:
  assert sha(ROOT/f["path"])==f["sha256"]
  assert sha(ROOT/f["validationPath"])==f["validationSha256"]
 source=source_rows(ROOT/"Source/localization-inventory-v3/strings.jsonl")
 static=source_rows(ROOT/"Source/localization-inventory-v3/static-text.jsonl")
 keys=set();static_ids=set();targets={};current_targets={};authored_paths={}
 by_collection_id={(r["collection"],r["stableId"].rsplit(":",1)[1]):r["stableId"] for r in source}
 for f in gate["files"]:
  data=j(ROOT/f["path"])
  if "collection" in data:
   for e in data["entries"]:
    keys.add((data["collection"],str(e["id"])))
    targets[(data["collection"],str(e["id"]))]=e["target"]
    sid=by_collection_id[(data["collection"],str(e["id"]))]
    current_targets[sid]=e["target"];authored_paths[sid]=f["path"]
  else:
   for e in data["entries"]:
    static_ids.add(e["stableId"])
    current_targets[e["stableId"]]=e["target"]
    authored_paths[e["stableId"]]=f["path"]
 accepted_source=[r for r in source if (r["collection"],r["stableId"].rsplit(":",1)[1]) in keys]
 accepted_static=[r for r in static if r["stableId"] in static_ids]
 rows=accepted_source+accepted_static
 ids=[r["stableId"] for r in rows];assert len(ids)==len(set(ids))==16538 and ih(ids)==old["sourceOrderIdListSha256LfFinalNewline"]
 assert set(current_targets)==set(ids)
 order={sid:k for k,sid in enumerate(ids)};by_id={r["stableId"]:r for r in rows}
 by_key=collections.defaultdict(list);by_source=collections.defaultdict(list)
 for r in accepted_source:
  by_key[r.get("key")].append(r["stableId"])
  src=re.sub(r"^[A-Za-z][A-Za-z0-9_]*: ","",r["source"])
  normalized=re.sub(r"[\s\u00a0]+"," ",src).replace("ё","е").replace("Ё","Е").strip()
  by_source[normalized].append(r["stableId"])
 components={k:set() for k in ("changed","sceneContext","repetition","glossaryReferent","runtimeBinding","mandatoryRegression")}
 changed={item["stableId"] for item in a["items"]}
 assert len(changed)==21 and changed<=order.keys()
 components["changed"]=changed
 for item in a["items"]:
  r=by_id[item["stableId"]]
  if "collection" not in r:continue
  src=re.sub(r"^[A-Za-z][A-Za-z0-9_]*: ","",r["source"])
  normalized=re.sub(r"[\s\u00a0]+"," ",src).replace("ё","е").replace("Ё","Е").strip()
  components["repetition"].update(by_source[normalized])
  # Exact old/new localized wording can carry a dependent repeated rendering.
  for sid in ids:
   row=by_id[sid]
   if "collection" not in row:continue
   target=targets[(row["collection"],sid.rsplit(":",1)[1])]
   if target in (item["before"],item["acceptedFullTarget"]):components["repetition"].add(sid)
 # These are finite source-language concept families invalidated by this batch.
 motifs={
  "psychics-plain-and-gag":r"Экстрасенс|Гавнасэнс",
  "armpit-plural-and-agreement":r"подмышк|волосат|грибк",
  "sun-greeting":r"здоровал|СОЛНЕЧН[А-ЯЁ]* ЛИДЕР",
  "guest-identity-discovery":r"оказал[а-яё]* Гостем",
  "completed-removal":r"забрал",
  "established-self":r"состоявш",
  "leave-alone-request":r"не трогай меня",
  "signs-plural":r"признак[а-яё]*|им доверять",
 }
 glossary_family={}
 for name,pattern in motifs.items():
  matcher=re.compile(pattern,re.IGNORECASE)
  members=[r["stableId"] for r in accepted_source if matcher.search(r["source"])]
  glossary_family[name]=members
  components["glossaryReferent"].update(members)
 # The reviewer read 82 specific Death/cult pairs for hidden speaker agreement.
 death=[json.loads(line) for line in (HI/"independent-review-01/supplementary-death-context.jsonl").read_text().splitlines()]
 assert len(death)==82
 for record in death:
  assert record["stableId"] in order
  components["glossaryReferent"].add(record["stableId"])
 glossary_family["ambiguous-death-speaker"]=[r["stableId"] for r in death]
 h=helper();nodes=runtime_nodes(h.fields)
 occurrences=collections.defaultdict(list)
 for name,ins in nodes.items():
  for pos,inst in enumerate(ins):
   for value in inst["strings"]:
    if value.startswith("line:"):occurrences[value].append((name,pos))
 characters=j(HI/"independent-review-01/character-placement-source-prefix.json")["rows"]
 by_name={r["name"].casefold():r for r in characters}
 ui_labels=collections.defaultdict(list)
 for r in accepted_source:
  k=r.get("key") or ""
  if r["collection"]=="UI" and k.startswith("characterName_"):
   ui_labels[k[len("characterName_"):].casefold()].append(r["stableId"])
 aliases={"twins":["AlkonostTwins","SirinTwins"],"sirin":["Sirin","SirinTwins"],"alkonost":["AlkonostTwins"]}
 technical=[];supplier_ids=set();uncompiled=[];dynamic_nodes=set()
 for item in a["items"]:
  sid=item["stableId"];r=by_id[sid];key=r.get("key")
  if not key:continue
  matched=occurrences.get(key,[])
  if not matched:
   family=key[5:].rsplit("_",1)[0] if key.startswith("line:") else None
   family_lines=[x["stableId"] for x in accepted_source if family and ((x.get("key") or "").startswith("line:"+family+"_") or family in x.get("nodeNames",[]))]
   components["sceneContext"].update(family_lines)
   uncompiled.append({"stableId":sid,"sourceKey":key,"inferredNode":family,"compiledNodeExists":family in nodes,"serializedFamilyIds":family_lines})
   continue
  for node,pos in matched:
   ins=nodes[node]
   line_inst=[x for x in ins if any(v.startswith("line:") for v in x["strings"])]
   line_keys=[v for x in line_inst for v in x["strings"] if v.startswith("line:")]
   position=line_keys.index(key)
   for near in line_keys[max(0,position-2):position+3]:components["sceneContext"].update(by_key[near])
   has_dynamic_supplier=any("GetCharacterOnPlace" in x["strings"] for x in ins)
   if not has_dynamic_supplier and "{0}" not in r["source"] and "{1}" not in r["source"]:continue
   dynamic_nodes.add(node)
   for line in line_keys:components["runtimeBinding"].update(by_key[line])
   for ii,inst in enumerate(ins):
    if "GetCharacterOnPlace" not in inst["strings"]:continue
    literal=next((ins[q]["strings"][0] for q in range(ii-1,-1,-1) if ins[q]["opcode"]==6 and ins[q]["strings"]),None)
    if not literal:continue
    owner=by_name.get(literal.casefold())
    if owner is None:continue
    place=owner["place"]
    candidates=[c for c in characters if c["place"]==place and c["name"]!=owner["name"]]
    linked=[]
    for c in candidates:
     names=[c["name"]]+aliases.get(c["name"].casefold(),[])
     for cname in names:
      for label_id in ui_labels[cname.casefold()]:
       supplier_ids.add(label_id);components["runtimeBinding"].add(label_id);linked.append(label_id)
    fragment={"node":node,"function":"GetCharacterOnPlace","lookupArgument":literal,"lookupCharacterPathId":owner["pathId"],"defaultPlace":place,"defaultCandidateCharacterPathIds":[c["pathId"] for c in candidates],"sourceBindingSha256":a["compiledRuntimeBindingsSha256"],"placementEvidenceSha256":sha(HI/"independent-review-01/character-placement-source-prefix.json")}
    fragment["fragmentSha256"]=hashlib.sha256(canonical(fragment)).hexdigest()
    technical.append(fragment)
 # Mandatory catalog: source IDs and predicates only; no Thai target wording.
 catalog_path=ROOT/"Documentation/th-semantic-regressions-v1.json"
 catalog=j(catalog_path)
 assert sha(catalog_path)=="3a5b89d4b4979f18983e84549f197d4fc5a4a954a360e5f31d79719e1e7fa5a6"
 group_ids={};required=set()
 for group in catalog["groups"]:
  members=group["ids"];assert len(members)==group["count"] and ih(members)==group["idsSha256"]
  assert set(members)<=set(ids)
  group_ids[group["name"]]=members;required.update(members)
 assert len(required)==4805
 components["mandatoryRegression"].update(required)
 components["mandatoryRegression"].update(old["components"]["mandatoryRegression"])
 assert required<=components["mandatoryRegression"]
 union=set().union(*components.values());assert union<=set(ids)
 ordered={name:[sid for sid in ids if sid in members] for name,members in components.items()}
 closure_ids=[sid for sid in ids if sid in union]
 prior=[r["stableId"] for r in old["reviewRows"]];assert len(prior)==1691 and ih(prior)==old["closureIdListSha256LfFinalNewline"]
 prior_set=set(prior)
 new=set(closure_ids)-prior_set
 retired=prior_set-set(closure_ids)
 # Re-read old reviewed units only when specific corrected family/scene/binding
 # evidence changed. The expanded mandatory catalog alone does not invalidate
 # an old read of an unchanged target.
 invalidated_members=components["sceneContext"]|components["repetition"]|components["glossaryReferent"]|components["runtimeBinding"]
 invalidated=(invalidated_members&prior_set)-changed
 delta_set=changed|new|invalidated
 delta_ids=[sid for sid in ids if sid in delta_set]
 assert delta_set==changed|(set(closure_ids)-prior_set)|invalidated
 assert not (retired&delta_set)
 tech_unique={x["fragmentSha256"]:x for x in technical}
 technical=list(tech_unique.values())
 context={"schemaVersion":1,"locale":"hi","status":"source-only runtime supplier fragments; not translated units","compiledRuntimeBindingsSha256":a["compiledRuntimeBindingsSha256"],"characterPlacementEvidenceSha256":sha(HI/"independent-review-01/character-placement-source-prefix.json"),"technicalFragmentCount":len(technical),"technicalFragments":technical,"translatedSupplierIds":[sid for sid in ids if sid in supplier_ids],"translatedSupplierIdListSha256LfFinalNewline":ih([sid for sid in ids if sid in supplier_ids]),"classification":"GetCharacterOnPlace function, literal lookup arguments, and serialized default places/candidate path IDs are technical. The compiled line keys and UI label IDs point to accepted translated units and are not themselves counted as nontranslatable fragments. Default candidates are static evidence, not exhaustive reachable game states."}
 context_text=json.dumps(context,ensure_ascii=False,indent=2)+"\n"
 context_sha=hashlib.sha256(context_text.encode()).hexdigest()
 result={"schemaVersion":1,"locale":"hi","gameVersion":"1.3.19","status":"repaired reproducible dependency closure; distinct delta review pending","acceptedCount":len(ids),"sourceOrderIdListSha256LfFinalNewline":ih(ids),"sourceInventorySha256":a["sourceInventorySha256"],"staticInventorySha256":a["staticInventorySha256"],"glossaryLayerSha256":a["glossaryLayerSha256"],"compiledRuntimeBindingsSha256":a["compiledRuntimeBindingsSha256"],"authoredStructuralGateSha256":sha(HI/"semantic-cycle-002-structural-gate.json"),"adjudicationSha256":sha(HI/"semantic-cycle-002-adjudication.json"),"previousClosureSha256":sha(HI/"semantic-cycle-001-closure.json"),"independentReview01Sha256":sha(HI/"independent-review-01/consolidated-full-unit-findings.json"),"catalogPath":"Documentation/th-semantic-regressions-v1.json","catalogSha256":sha(catalog_path),"catalogRequiredCount":len(required),"catalogRequiredIdListSha256LfFinalNewline":ih([sid for sid in ids if sid in required]),"technicalContextPath":"Translations/hi/semantic-cycle-002-runtime-context.json","technicalContextSha256":context_sha,"changedCount":len(changed),"closureCount":len(closure_ids),"closureIdListSha256LfFinalNewline":ih(closure_ids),"componentCounts":{k:len(v) for k,v in ordered.items()},"componentIdListSha256LfFinalNewline":{k:ih(v) for k,v in ordered.items()},"components":ordered,"glossaryReferentMotifs":motifs,"glossaryFamilyCounts":{k:len(v) for k,v in glossary_family.items()},"mandatoryCatalogGroupCounts":{k:len(v) for k,v in group_ids.items()},"uncompiledChangedRows":uncompiled,"changedRuntimeNodes":sorted(dynamic_nodes),"missingRequiredCatalogIds":[],"extraUnacceptedIds":[],"reviewRows":[{"stableId":sid,"reviewIndex":order[sid],"source":by_id[sid]["source"],"target":current_targets[sid],"sourceSha256":hashlib.sha256(by_id[sid]["source"].encode()).hexdigest(),"targetSha256":hashlib.sha256(current_targets[sid].encode()).hexdigest(),"authoredPath":authored_paths[sid],"components":[k for k,v in components.items() if sid in v]} for sid in closure_ids],"selectorMethod":"Accepted source order; exact normalized repetitions and target echoes; bounded glossary/referent motifs; actual compiled instruction neighborhoods, whole changed dynamic nodes, raw UI supplier labels from serialized default places; all 4,805 source-risk catalog IDs plus prior mandatory surfaces."}
 delta={"schemaVersion":1,"locale":"hi","gameVersion":"1.3.19","status":"exact next independent delta; not yet reviewed","previousIndependentlyReviewedClosureSha256":sha(HI/"semantic-cycle-001-closure.json"),"previousIndependentlyReviewedCount":len(prior),"currentClosureCount":len(closure_ids),"currentClosureIdListSha256LfFinalNewline":ih(closure_ids),"correctedIds":[sid for sid in ids if sid in changed],"correctedCount":len(changed),"newDependencyIds":[sid for sid in ids if sid in new],"newDependencyCount":len(new),"explicitInvalidatedPriorIds":[sid for sid in ids if sid in invalidated],"explicitInvalidatedPriorCount":len(invalidated),"invalidationReason":"Prior read evidence intersects current correction's scene context, exact repetition, bounded glossary/referent family, or actual runtime binding. Mere overlap with the newly complete mandatory catalog is not an invalidation.","retiredIds":[sid for sid in ids if sid in retired],"retiredCount":len(retired),"retirementReason":"These cycle-001 dependencies no longer intersect cycle-002 corrected families, binding, or mandatory catalog; their review01 evidence remains preserved and unchanged targets need no new read.","deltaIds":delta_ids,"deltaCount":len(delta_ids),"deltaIdListSha256LfFinalNewline":ih(delta_ids),"formula":"corrected IDs union (current closure minus previous independently reviewed closure) union explicit invalidated prior IDs","missingAcceptedIds":[],"extraUnacceptedIds":[]}
 result["selectorSha256"]=sha(Path(__file__))
 for name in ("correctedIds","newDependencyIds","explicitInvalidatedPriorIds","retiredIds"):
  delta[name+"Sha256LfFinalNewline"]=ih(delta[name])
 return (context_text,json.dumps(result,ensure_ascii=False,indent=2)+"\n",json.dumps(delta,ensure_ascii=False,indent=2)+"\n",result,delta)
def main():
 parser=argparse.ArgumentParser();parser.add_argument("--verify",action="store_true");args=parser.parse_args()
 texts=build();outputs=(CONTEXT,OUT,DELTA)
 if args.verify:
  for path,text in zip(outputs,texts[:3]):assert path.read_text(encoding="utf-8")==text,path
  print("verified",texts[3]["closureCount"],"closure IDs;",texts[4]["deltaCount"],"delta IDs")
 else:
  assert not any(path.exists() for path in outputs)
  for path,text in zip(outputs,texts[:3]):path.write_text(text,encoding="utf-8")
  print("wrote",texts[3]["closureCount"],"closure IDs;",texts[4]["deltaCount"],"delta IDs")
  print("components",texts[3]["componentCounts"],"new",texts[4]["newDependencyCount"],"invalidated",texts[4]["explicitInvalidatedPriorCount"],"retired",texts[4]["retiredCount"])
if __name__=="__main__":main()
