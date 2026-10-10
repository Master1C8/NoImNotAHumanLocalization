"""Ordinary bounded profanity selectors; literal plant spans are context, not swears."""
import re

def masked_source(source,spec):
 result=source
 for pattern in spec['literalHorseradishContextRegex']:
  result=re.sub(pattern,lambda m:' '*len(m.group()),result)
 return result

def source_matches(name,pattern,source,spec):
 tested=masked_source(source,spec) if name in ['profanity-humor','coarse-xren-xer'] else source
 return bool(re.search(pattern,tested))
