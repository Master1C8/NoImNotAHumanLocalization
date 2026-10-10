"""Record reviewer-authored full-unit wording decisions after all 18 pairs were read."""
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;C=R/'Translations/fa/audit-cycle-003'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,d):
 b=(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode();p=O/n
 if p.exists():assert p.read_bytes()==b
 else:p.write_bytes(b)
notes={
 '110504452794949632':'The threat preserves their relaxing, forgetting who enabled their presence, and consequent nonpayment; no agency or payment reversal.',
 '110504452790755337':'The idiom keeps the targets alert/on their toes, matching the following threat without adding an event.',
 '110504452790755336':'First-person scammer refuses being conned and redirects warming up the gullible people for payment; insult and participant direction retained.',
 '110504452790755329':'Accepted complete correction: Russian identifies one aunt with unspecified family side. Persian singular عمه یا خاله‌ام uses disjunction, not two relatives; possessive suffix has shared scope. The construction is understandable and grammatically acceptable colloquial Persian, though its explicit alternatives are more conspicuous than Russian. Neither side is asserted. This is not an objective reason for another stylistic rewrite. Losing her house in cards, first-person agent, less severe prior consequences, comparison with the present photo, Scammer prefix and ellipsis all remain. No placeholder/join or factual sentence was omitted.',
 '110504452790755328':'Colloquial incredulity in the gun confrontation is retained as a statement that the player is joking.',
 '110504452786561029':'Confirmation question preserves the request for reassurance after showing the ear.',
 '110504452786561028':'Exact silent ellipsis retains its speaker and does not invent dialogue.',
 '110504452786561027':'Scammer offers his own ear while warning the player against using the same abusive scam on him; direction and rough register retained.',
 '110504452786561026':'The sequence of inspection, asserting a Visitor-related condition inside, demanding the inspected person’s money and promising nondisclosure remains. No guaranteed diagnosis is added; approved Visitors usage retained. Prior unchanged meaning decision is not reversed without new evidence.',
 '110504452786561025':'Boast that he invented the scam first preserves priority, agent and familiar protest.',
 '110504452782366728':'Conditional photo outcome preserves dirty camera, resulting spots, and dismissive profanity.',
 '110504452782366727':'Alternate photo outcome preserves only the visible silhouette and wasted posing; person/photograph referents remain clear.',
 '110504452782366726':'The callback remains an immediate reference to his preceding warning; no new explanatory fact.',
 '110504452782366725':'Exact silent ellipsis preserves the pause before the callback.',
 '110504452782366724':'High light sensitivity and possible movement are retained as his explanation, with possibility rather than certainty.',
 '110504452782366723':'Casual photo invitation and willingness to proceed retain addressee and shared action.',
 '110504452010614786':'The death-branch insult remains sexually vulgar and cut off. Persian begins the object slang and stops at the opening of the imperative verb; it preserves an interrupted obscene utterance rather than completing it. Scammer speaker prefix and ellipsis retained.',
 '110504452010614785':'Death-branch incredulity remains a question directed at the player before Kill Scammer; no role or chronology change.'
}
rows=json.loads((C/'next-review-delta.json').read_text())['rows'];assert len(rows)==len(notes)==18
out=[]
for ordinal,r in enumerate(rows,1):
 h=hashlib.sha256(json.dumps({k:r[k] for k in ['stableId','source','target']},ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
 out.append({**r,'ordinal':ordinal,'fullPairSha256':h,'read':'Independent complete Russian/Persian full unit read; complete current replacement assessed','outcome':'accepted; no objective wording correction','findingId':None,'reasonedDecision':notes[r['stableId'].rsplit(':',1)[1]],'glossaryContext':'Approved amogus-shirt-man male character, boastful familiar vulgar voice; player male; Visitors and inspect/shoot/listen meanings retained; aunt side absent from approved source and fa glossary','consumerContext':'Actual compiled photo/gun/listen/death and ear nodes; gun order two dialogue lines then Shoot and Listen options; first branch Kill Scammer before interrupted final line','runtimeLimit':'Logical authored units and compiled topology only; live bidi/shaping/ZWNJ/font/layout/progression not run'})
put('per-id-review.json',{'schemaVersion':1,'reviewer':'/root/fa_independent_review_03','gameVersion':'1.3.19','sourceLocale':'ru','locale':'fa','closureSha256':sha(C/'closure.json'),'deltaSha256':sha(C/'next-review-delta.json'),'reviewedUnits':18,'reviewedIdsSha256':sha(C/'nextReviewDelta-ids.txt'),'fullPairHashEncoding':'UTF-8 compact JSON ordered stableId,source,target; ensure_ascii false; no terminal LF','reviewRows':out})
put('findings.json',{'schemaVersion':1,'reviewer':'/root/fa_independent_review_03','objectiveProposals':0,'rows':[],'completeDeltaRead':18,'auntFullReplacementAccepted':True,'preferenceRewriteAvoided':True,'unboundedSystemicFinding':False})
print('Recorded 18 full-unit decisions; zero objective proposals.')
