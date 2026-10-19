from engine.targeting import geography,phone_text,classify

def test_location_gate():
 assert geography('','Pune','')=='OUTSIDE_WB'
 assert geography('','Mumbai','')=='OUTSIDE_WB'
 assert geography('West Bengal','Pune','')=='REVIEW_REQUIRED'
 assert geography('','Madanpur','')=='GEO_UNKNOWN'
 assert geography('WB','Kalyani','')=='WB_CONFIRMED'
def test_scientific_phone():
 assert phone_text('9.230003028E+9')[0]=='919230003028'
 assert phone_text(9230003028.0)[0]=='919230003028'
 assert phone_text('9230003028 / 9007129816')[0]==''
def test_outside_never_included():
 r=classify(dict(state='Maharashtra',city='Pune',address='',company='Steel manufacturer',sector=''))
 assert r['lakhotia_class']=='N'
def test_wb_sector_research_only():
 r=classify(dict(state='WB',city='Howrah',address='',company='Steel manufacturer',sector=''))
 assert r['lakhotia_class']=='P2'

def test_state_only_relevant_company_is_kept_for_geography_review():
 r=classify(dict(state='West Bengal',city='',address='',company='Steel manufacturer',sector='manufacturing'))
 assert r['geo_status']=='WB_POSSIBLE'
 assert r['lakhotia_class']=='REVIEW_REQUIRED'
 assert 'GEO_REVIEW_REQUIRED_WITH_PROFILE_RELEVANCE' in r['reason_codes']

def test_lakhotia_published_industry_signals_are_research_only():
 for sector in ('Plastics and packaging','Pharmaceuticals','Agro-processing','Electrical cable manufacturing','Garment fabrication','3PL warehousing'):
  r=classify(dict(state='WB',city='Howrah',address='',company='',sector=sector))
  assert r['lakhotia_class']=='P2'
  assert 'OBSERVED_PROFILE_RELEVANCE_ONLY' in r['reason_codes']

def test_ai_does_not_send_contacts_or_promote(tmp_path,monkeypatch):
 from engine import ai
 seen=[]
 def fake(evidence):
  seen.append(evidence);return {'project':'lakhotia','evidence_quote':'Howrah','reason':'review'}
 monkeypatch.setattr(ai,'suggest',fake)
 r=dict(state='WB',city='Howrah',address='',company='Unknown',sector='',geo_status='WB_CONFIRMED',lakhotia_class='N',shree_class='N',vrindavan_class='N',name='SECRET_NAME',phone_normalized='919999999999')
 ai.annotate([r],tmp_path/'cache.json',1)
 assert 'SECRET_NAME' not in seen[0] and '919999999999' not in seen[0]
 assert r['lakhotia_class']=='N' and r['ai_status']=='SUGGESTION_REQUIRES_REVIEW'
 assert ai.annotate([r],tmp_path/'cache.json',1)==0
