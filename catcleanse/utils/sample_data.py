"""Generate ten realistic but deliberately untidy Kenyan portfolio rows."""
import pandas as pd

def sample_portfolio():
    """Return representative, intentionally inconsistent demo data."""
    rows=[
      {"Property Ref":"NRB-001","Property Name":"Kilimani Plaza","Address":"Kindaruma Rd, Kilimani, Nairobi","Occupancy":"commercial offices","Construction":"reinforced concrete frame","Stories":"8 floors","Year Built":2008,"Building Value":"KES 85M","Contents":"KES 12,500,000"},
      {"Property Ref":"NRB-002","Property Name":"Westgate Annex","Address":"Westlands, Nairobi","Occupancy":"shops","Construction":"glass and steel frame","Stories":5,"Year Built":2014,"Building Value":"USD 2.1M","Latitude":-1.263,"Longitude":36.803},
      {"Property Ref":"NRB-003","Property Name":"Muthaiga Court","Address":"Parklands Road, Westlands","Occupancy":"apartments","Construction":"stone and cement block","Building Value":"50,000,000 KES","Stories":"6 storeys"},
      {"Property Ref":"NRB-004","Property Name":"South C Warehse","Address":"South C near Nairobi River basin","Occupancy":"industrial warehouse","Construction":"steel frame","Building Value":"KES 120,000,000","Year Built":1998},
      {"Property Ref":"NRB-005","Property Name":"Eastleigh Mall","Address":"Eastleigh, Nairobi","Occupancy":"commercial","Construction":"masonry brick","Stories":"3 floors","Building Value":"5M KES","Contents":"Ksh 850k"},
      {"Property Ref":"NRB-006","Property Name":"Karen Family Home","Address":"Karen, Nairobi","Occupancy":"single family residential","Construction":"reinforced concrete","Year Built":2019,"Building Value":"KES 45 million"},
      {"Property Ref":"NRB-007","Property Name":"CBD Towers","Address":"Central Business District, Nairobi","Occupancy":"commercial offices","Construction":"reinforced concrete","Stories":14,"Building Value":"KES 350,000,000","Latitude":-1.286,"Longitude":36.817},
      {"Property Ref":"NRB-008","Property Name":"Runda Residence","Address":"Runda estate, Nairobi","Occupancy":"residential house","Construction":"timber roof, masonry walls","Building Value":"KES 63M","Year Built":"unknown"},
      {"Property Ref":"NRB-009","Property Name":"Embakasi Depot","Address":"Embakasi, Nairobi","Occupancy":"industrial","Construction":"steel frame","Stories":"2","Building Value":"KES 0","Latitude":40.7,"Longitude":-1.2},
      {"Property Ref":"NRB-010","Property Name":"Thika Rd Apts","Address":"Thika Road corridor, Nairobi","Occupancy":"multi-family residential","Construction":"masonry","Stories":"10 floors","Building Value":"KES 110,000,000","Contents":"KES 8M"},
    ]
    return pd.DataFrame(rows)
