#!/usr/bin/env python3
"""Prepare the author's complete Hindi cycle-002 full-unit correction proposal."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HI=ROOT/"Translations/hi"
OUT=HI/"semantic-cycle-002-adjudication.json"
# Every replacement was authored directly against pinned Russian and approved glossary.
TARGETS={
"110504457236717576":"Twins: मुझे लगता है उस व्यक्ति की तरफ़ से मेरी छोटी बहन पर तानों की बौछार होगी।",
"110504457165414403":"Fanatic: इंसान! जब तक इस घर में {0} छिपकर मौजूद है, सूरज ने मुझे अंदर आने से मना किया है।",
"110504452639760390":"Fanatic: क्या किसी ने तुम्हें बताया कि मैंने ख़ुद सूर्य नेता का अभिवादन किया था?",
"110504452501348361":"Wheelchair: अगर… अगर तुझे इस लक्षण पर भरोसा नहीं, तो मैं उन पर कैसे करूँ?",
"110504451985448963":"Widow: जो चाहो करो, बस मुझे अकेला छोड़ दो।",
"110504455412195339":"FormerFema: एक बार मैं अतिथि के लक्षण वाले एक और आदमी को ले गया था।",
"110504454741106690":"Bestson: अगर दादी अतिथि निकली हों और उन्हें मार दिया हो तो? अगर आपात समिति ने रोककर उन्हें ले लिया हो तो…",
"110504455756128261":"Experienced: मैं अब अपने ढंग में ढल चुका इंसान हूँ, ज़िंदगी भी वैसे ही अंत की ओर बढ़ रही है।",
"110504456024563717":"मुझे समझ में आ रहा है कि तुम तैयार हो।",
"110504456024563718":"यह तय है कि मैं तुम्हें उस रात में ले जाऊँ, जहाँ चीड़ का पेड़ तारे तक पहुँचता है।",
"110504456011980809":"मुझे दिख रहा है कि तुम ‘हाँ’ कहोगे।",
"110504452341964800":"Buddy: देखने लायक कुछ नहीं है, सच कह रहा हूँ। मोटी, बालों वाली, ऊपर से कोई फफूँद भी है। शायद तब लगी जब कुत्ते के साथ फ़र्श पर सोया था।",
"tmp:level1:3842:m_text":"अतींद्रिय विशेषज्ञों की सेवा",
"tmp:level1:4228:m_text":"अतींद्रिय विशेषज्ञों की सेवा",
"tmp:level1:4275:m_text":"अतींद्रिय विशेषज्ञों की सेवा",
"110504457152831498":"Couple: ओह, आपको परेशान करना अच्छा नहीं लग रहा, मगर पास में {0} हो तो हम यहाँ नहीं रह पाएँगे...",
"110504457366740994":"Experienced: मुझे यह अच्छा नहीं लगता कि यहाँ {0} है।",
"110504457186385920":"NotTrue: अरे बाप रे! तुम्हारी कुर्सी पर पहले से {0} है।",
"110504457131859968":"Buddy: ओह, यार, देख रहा हूँ कि तुम्हारे यहाँ पहले से {0} है—जगह गरमा रखी है।",
"110504457245106180":"Wolfhound: तुम्हारे यहाँ पहले से {0} आग तापने में व्यस्त है? देखते ही समझ गया, वह भेड़ की खाल में छिपी मादा भेड़िया है।",
"110504451758956544":"Wheelchair: तू बगलें दिखाने को कहता है और मैं दिखा देता हूँ।",
}
ADDITIONAL={
"110504457152831498":"Raw occupant label preceded के; Couple place 12 includes a masculine direct-case label. Move slot before invariant हो and retain near-neighbor condition.",
"110504457366740994":"Experienced place 12 includes Daughter. Old जँचता assigns masculine agreement to a variable occupant. New predicate refers to invariant यह.",
"110504457186385920":"NotTrue place 32 includes female Sirin/Twins. Old बैठा assigns masculine agreement to the variable occupant. Chair location still conveys sitting.",
"110504457131859968":"Buddy place 65 includes female Wifefema. Old जमा assigns masculine agreement. New है is invariant and गरमा रखी agrees with जगह.",
"110504457245106180":"WolfHound place 33 includes male Fairytaller and female Nun/Ballerina. Old बैठी assigns female agreement to occupant. Source she-wolf metaphor remains speech, not a biological assertion.",
"110504451758956544":"Russian подмышки is plural; old बगल narrows inspected body parts. All 92 source matches were enumerated.",
}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def main():
 assert len(TARGETS)==21 and not OUT.exists()
 progress=read(HI/"semantic-review-progress.json")
 review=read(HI/"independent-review-01/consolidated-full-unit-findings.json")
 gate=read(HI/"semantic-cycle-001-structural-gate.json")
 closure=read(HI/"semantic-cycle-001-closure.json")
 source=[json.loads(l) for p in (ROOT/"Source/localization-inventory-v3/strings.jsonl",ROOT/"Source/localization-inventory-v3/static-text.jsonl") for l in p.read_text().splitlines()]
 sources={r["stableId"]:r for r in source}
 by_key={(r["collection"],r["stableId"].rsplit(":",1)[1]):r["stableId"] for r in source if "collection" in r}
 target={};files={}
 for f in gate["files"]:
  path=ROOT/f["path"];assert sha(path)==f["sha256"]
  d=read(path)
  for e in d["entries"]:
   sid=e["stableId"] if "stableId" in e else by_key[(d["collection"],str(e["id"]))]
   assert sid not in target
   target[sid]=e["target"];files[sid]=f["path"]
 assert len(target)==16538
 accepted=[r["stableId"] for r in source if r["stableId"] in target]
 assert hashlib.sha256(("\n".join(accepted)+"\n").encode()).hexdigest()==progress["reviewOrderIdListSha256LfFinalNewline"]
 index={sid:i for i,sid in enumerate(accepted)}
 by_suffix={sid.rsplit(":",1)[1]:sid for sid in target if sid.startswith("string:")}
 reviewed={u["stableId"]:f for f in review["findings"] for u in f["units"]}
 prior={r["stableId"] for r in closure["reviewRows"]}
 items=[]
 for key,new in TARGETS.items():
  sid=key if key.startswith("tmp:") else by_suffix[key]
  r=sources[sid];old=target[sid];assert old!=new
  finding=reviewed.get(sid);assert (finding is None)==(key in ADDITIONAL)
  items.append({"stableId":sid,"reviewIndex":index[sid],"sourceKey":r.get("key"),"source":r["source"],"sourceSha256":hashlib.sha256(r["source"].encode()).hexdigest(),"authoredPath":files[sid],"before":old,"acceptedFullTarget":new,"reason":finding["reason"] if finding else ADDITIONAL[key],"findingGroup":finding["findingId"] if finding else "HI-AUTHOR-BOUNDED-001","inPreviousClosure":sid in prior})
 items.sort(key=lambda r:r["reviewIndex"])
 assert sum(i["findingGroup"].startswith("HI-IR01") for i in items)==15
 out={"schemaVersion":1,"locale":"hi","gameVersion":"1.3.19","sourceLocale":"ru","status":"complete author-adjudicated full-unit proposal; preflight and application pending","sourceInventorySha256":sha(ROOT/"Source/localization-inventory-v3/strings.jsonl"),"staticInventorySha256":sha(ROOT/"Source/localization-inventory-v3/static-text.jsonl"),"glossaryLayerSha256":sha(ROOT/"Documentation/glossary-translations/hi/layer.json"),"compiledRuntimeBindingsSha256":sha(ROOT/"Source/glossary-corpus-v2/runtime-bindings.json"),"independentReviewFindingsSha256":sha(HI/"independent-review-01/consolidated-full-unit-findings.json"),"previousClosureSha256":sha(HI/"semantic-cycle-001-closure.json"),"acceptedCount":len(items),"independentFindingGroups":11,"independentProposedUnits":15,"additionalBoundedFindings":6,"dismissedQuestion":{"key":"line:Theorist_Asking_2_04f4138","decision":"Retain current target. It names the approved emergency committee and explicitly introduces an alternate acronym expansion. Matching Hindi initials would require an invented or altered approved name. No objective fact is contradicted; preserve as an adaptation question for independent judgment."},"boundedRemedialRead":{"deathCultPairs":82,"armpitFamilySourceMatches":92,"psychicsSourceMatches":14,"chronologySourceMatches":14,"greetingSourceMatches":4,"dynamicPlaceholders":111,"method":"Enumerated pinned accepted IDs and read matched complete source/target with scene, placement and glossary context. This is bounded, not a new full-corpus semantic audit."},"items":items}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
 print("prepared",len(items),"replacements: 15 reviewer, 6 bounded")
if __name__=="__main__":main()
