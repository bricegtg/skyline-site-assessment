"""
Skyline Site Assessment — Service Question Schemas
====================================================
Each service has its own schema of sections and fields. The schema is
the single source of truth used by:
  - The frontend form renderer (served as JSON at /api/schemas)
  - The backend PDF generator (renders sections in the same order)
  - The CRM deal auto-creation (extracts key fields into the Deal payload)

Field spec:
  {
    "key":     "snake_case_key",       # column-like identifier
    "label":   "Human question text",  # shown in the form
    "type":    "text" | "textarea" | "number" | "select" | "multiselect" |
               "checkbox" | "radio" | "yesno" | "date",
    "required": bool (optional, default False),
    "options":  [str] (for select/multiselect/radio),
    "unit":     "sqm"|"m"|"PHP"|"km" (optional, shown as suffix),
    "help":     "Extra context shown under the field" (optional),
  }
"""

from copy import deepcopy


# -----------------------------------------------------------------
# Shared sections used across ALL services
# -----------------------------------------------------------------

CONTACT_SECTION = {
    "id": "contact",
    "title": "Contact & Property Identification",
    "description": "Primary contact and legal invoicing details for the property in scope.",
    "fields": [
        {"key": "property_name",    "label": "Property name",                 "type": "text",     "required": True},
        {"key": "property_address", "label": "Property address (street, city, region)", "type": "textarea", "required": True},
        {"key": "gps_coordinates",  "label": "GPS coordinates (if available)","type": "text"},
        {"key": "primary_contact_name", "label": "Primary contact name",      "type": "text",     "required": True},
        {"key": "primary_contact_role", "label": "Role / title",              "type": "text"},
        {"key": "primary_contact_email","label": "Contact email",             "type": "text",     "required": True},
        {"key": "primary_contact_phone","label": "Contact phone",             "type": "text",     "required": True},
        {"key": "billing_entity",   "label": "Preferred billing entity (legal name for invoicing)", "type": "text", "required": True},
        {"key": "tin_vat",          "label": "TIN / VAT registration number (for BIR-compliant invoicing)", "type": "text"},
        {"key": "po_number",        "label": "Purchase order or reference number (if applicable)", "type": "text"},
    ],
}

URGENCY_SECTION = {
    "id": "urgency",
    "title": "Urgency & Timing",
    "fields": [
        {"key": "urgency_level", "label": "Urgency level", "type": "radio", "required": True,
         "options": ["Standard (Skyline scheduling)", "Rush (expedited mobilisation — surcharge applies)"]},
        {"key": "operating_hours_preference", "label": "Operating hours preference", "type": "multiselect",
         "options": ["Standard daytime (0500–1700)", "Off-peak / dawn / dusk", "Weekend only", "Mall closing hours only (retail assets)", "Night operations (with lighting)"]},
        {"key": "target_service_date", "label": "Target service start date", "type": "date"},
        {"key": "hard_deadlines",  "label": "Hard deadlines (pre-Christmas retail, corporate event, tenant handover, ESG report cut-off)", "type": "textarea"},
        {"key": "blackout_dates",  "label": "Blackout dates / no-fly periods (promotions, VIP visits, tenant events)", "type": "textarea"},
    ],
}

ACCESS_SAFETY_SECTION = {
    "id": "access_safety",
    "title": "Access, Safety & Site Conditions",
    "fields": [
        {"key": "airport_proximity_km", "label": "Property proximity to nearest airport", "type": "number", "unit": "km"},
        {"key": "class_d_airspace",     "label": "Within 10 km of NAIA, Clark, Cebu-Mactan, or any Class D airspace?", "type": "yesno"},
        {"key": "caap_clearance",       "label": "Existing CAAP airspace clearance or LGU permits on file?", "type": "yesno"},
        {"key": "rooftop_access",       "label": "Rooftop access available for equipment staging?", "type": "yesno"},
        {"key": "ground_dropzone",      "label": "Ground perimeter / drop-zone available?", "type": "yesno"},
        {"key": "overhead_constraints", "label": "Adjacent building or overhead constraints (power lines, structures within 15 m)", "type": "textarea"},
        {"key": "rf_interference",      "label": "Radio frequency interference sources on site (radar, high-power antennae, comms towers)", "type": "textarea"},
        {"key": "parking",              "label": "On-site parking available for support vehicles? (number of spaces)", "type": "text"},
    ],
}

COMPLIANCE_SECTION = {
    "id": "compliance",
    "title": "Compliance, Insurance & Documentation",
    "fields": [
        {"key": "coi_required",        "label": "Certificate of insurance (COI) required prior to mobilisation?", "type": "yesno"},
        {"key": "insurance_limits",    "label": "Required insurance coverage limits (if higher than Skyline standard ₱100,000 TPL)", "type": "text"},
        {"key": "prequal_docs",        "label": "Required contractor pre-qualification documents (list)", "type": "textarea"},
        {"key": "safety_induction",    "label": "Facility-specific safety induction required prior to start? (describe)", "type": "textarea"},
        {"key": "esg_reporting",       "label": "ESG / sustainability reporting requirements (water use, chemical disclosure, CO₂ avoided)", "type": "textarea"},
        {"key": "green_certification", "label": "LEED / EDGE / BERDE certification on this property? (level)", "type": "text"},
        {"key": "reporting_cadence",   "label": "Preferred reporting cadence", "type": "radio",
         "options": ["Per-service report", "Monthly summary", "Quarterly ESG rollup"]},
    ],
}

FINANCIAL_SECTION = {
    "id": "financial",
    "title": "Financial & Commercial",
    "fields": [
        {"key": "payment_terms", "label": "Preferred payment terms", "type": "radio", "required": True,
         "options": [
             "30% deposit / 70% on completion",
             "50% deposit / 50% on completion (Skyline standard)",
             "Milestone-based",
             "Net 30 / Net 45 / Net 60 (post-service)",
         ]},
        {"key": "payment_terms_notes", "label": "Milestone details or other payment notes", "type": "textarea"},
        {"key": "currency", "label": "Preferred currency", "type": "select", "options": ["PHP", "USD", "SAR", "AED"]},
        {"key": "vat_treatment", "label": "Quote VAT-inclusive or VAT-exclusive?", "type": "radio",
         "options": ["VAT-exclusive at 12% (Skyline standard)", "VAT-inclusive"]},
        {"key": "withholding_tax", "label": "Withholding tax applicable? (rate if yes)", "type": "text"},
        {"key": "budget_range",    "label": "Budget range or benchmark against current supplier (PHP)", "type": "text"},
        {"key": "current_annual_spend", "label": "Existing annual maintenance spend on this property (PHP)", "type": "number", "unit": "PHP"},
        {"key": "preferred_bank",  "label": "Preferred bank / payment method", "type": "text"},
    ],
}

DECISION_SECTION = {
    "id": "decision",
    "title": "Comparative & Decision Criteria",
    "fields": [
        {"key": "current_method", "label": "Current method for this service (if any)", "type": "text"},
        {"key": "current_frequency", "label": "Current cleaning / service frequency", "type": "text"},
        {"key": "primary_reasons", "label": "Primary reasons for evaluating Skyline (rank top 3)", "type": "multiselect",
         "options": [
             "Safety / CAAP compliance", "Cost reduction", "Speed / reduced downtime",
             "Sustainability / ESG", "Guest / tenant experience", "Reduced insurance exposure",
             "Innovation / brand positioning", "Portfolio standardisation",
         ]},
        {"key": "decision_stakeholders", "label": "Key stakeholders in the decision", "type": "textarea"},
        {"key": "target_decision_date", "label": "Target decision date", "type": "date"},
    ],
}

NOTES_SECTION = {
    "id": "notes",
    "title": "Notes & Additional Information",
    "fields": [
        {"key": "additional_notes", "label": "Free-text notes, special instructions, or additional context", "type": "textarea"},
    ],
}


# -----------------------------------------------------------------
# SERVICE 1: FACADE / BUILDING CLEANING (from the July 2026 questionnaire)
# -----------------------------------------------------------------

FACADE_CLEANING = {
    "id": "facade_cleaning",
    "name": "Facade / Building Cleaning",
    "tagline": "Drone-powered exterior facade cleaning proposal — property survey",
    "sections": [
        deepcopy(CONTACT_SECTION),
        {
            "id": "classification",
            "title": "Property Type & Classification",
            "fields": [
                {"key": "building_type", "label": "Building type", "type": "radio", "required": True,
                 "options": [
                     "Commercial Towers & Skyscrapers (office towers, mixed-use towers)",
                     "Hotels, Resorts & Hospitality",
                     "Government & Civic Buildings",
                     "Airports & Aviation Infrastructure",
                     "Oil & Gas Facilities",
                     "Office Campuses & Business Parks",
                     "Industrial & Logistics Buildings",
                     "Public Infrastructure & Stadiums",
                     "Shopping Mall / Retail",
                     "Residential (mid-rise / high-rise condominium)",
                 ]},
                {"key": "portfolio_role", "label": "Portfolio role (all that apply)", "type": "multiselect",
                 "options": [
                     "DMWAI-owned / leased asset",
                     "Aseana City office tower (Aseana Business Park)",
                     "Retail / mixed-use (Parqal, ASEANA Square)",
                     "Hospitality",
                     "Residential",
                     "Co-living / serviced residences",
                     "Commercial lot / build-to-suit lease",
                 ]},
            ],
        },
        {
            "id": "dimensions",
            "title": "Building Dimensions",
            "description": "Physical envelope of the property. These values drive the cleaning-area calculation.",
            "fields": [
                {"key": "facade_area_sqm",   "label": "Total facade area for cleaning", "type": "number", "unit": "sqm", "required": True},
                {"key": "floors_above",      "label": "Number of floors above ground",  "type": "number", "required": True},
                {"key": "height_m",          "label": "Overall building height (ground to parapet)", "type": "number", "unit": "m", "required": True},
                {"key": "highest_cleanable_m", "label": "Height to highest cleanable point", "type": "number", "unit": "m"},
                {"key": "num_facades",       "label": "Number of distinct facades / building faces (1–8)", "type": "number", "required": True},
                {"key": "roof_footprint_sqm","label": "Roof footprint area", "type": "number", "unit": "sqm"},
                {"key": "podium_facade_sqm", "label": "Podium / low-rise annex facade area", "type": "number", "unit": "sqm"},
                {"key": "curved_area_sqm",   "label": "Curved, sloped, or non-planar facade area", "type": "number", "unit": "sqm"},
            ],
        },
        {
            "id": "materials",
            "title": "Facade Material Composition",
            "description": "For each facade, indicate the primary material and approximate coverage %.",
            "fields": [
                {"key": "facade_1", "label": "Facade 1 — orientation (N/S/E/W) · primary material · coverage %", "type": "text"},
                {"key": "facade_2", "label": "Facade 2 — orientation · primary material · coverage %", "type": "text"},
                {"key": "facade_3", "label": "Facade 3 — orientation · primary material · coverage %", "type": "text"},
                {"key": "facade_4", "label": "Facade 4 — orientation · primary material · coverage %", "type": "text"},
                {"key": "facade_5_plus", "label": "Facade 5+ — orientation · primary material · coverage %", "type": "text"},
                {"key": "condition_notes", "label": "Notes on facade condition (salt-air exposure, pollutant load, algae, staining, coating age)", "type": "textarea"},
            ],
        },
        {
            "id": "addons",
            "title": "Add-On Scope",
            "fields": [
                {"key": "addons", "label": "Additional cleaning scopes to include", "type": "multiselect",
                 "options": [
                     "Balcony cleaning", "AC unit exterior cleaning", "Solar panel cleaning",
                     "Rooftop cleaning", "Signage / logo cleaning",
                     "Louver / brise-soleil / architectural feature cleaning",
                     "Interior atrium high-level cleaning", "Skylight cleaning",
                 ]},
                {"key": "num_balconies", "label": "Approximate number of balconies (if selected)", "type": "number"},
                {"key": "num_ac_units",  "label": "Approximate number of visible external AC units", "type": "number"},
                {"key": "solar_array_sqm","label": "Total solar array area (if applicable)", "type": "number", "unit": "sqm"},
                {"key": "rooftop_area_sqm","label": "Rooftop area (if applicable)", "type": "number", "unit": "sqm"},
                {"key": "skylight_area_sqm","label": "Skylight area (if applicable)", "type": "number", "unit": "sqm"},
            ],
        },
        {
            "id": "frequency",
            "title": "Service Frequency & Contract Structure",
            "fields": [
                {"key": "service_frequency", "label": "Preferred service frequency", "type": "radio", "required": True,
                 "options": ["One-time engagement", "Bi-annual", "Quarterly", "Multi-year", "Custom cadence"]},
                {"key": "custom_cadence", "label": "Custom cadence details (if selected)", "type": "text"},
            ],
        },
        deepcopy(URGENCY_SECTION),
        {
            **deepcopy(ACCESS_SAFETY_SECTION),
            "fields": ACCESS_SAFETY_SECTION["fields"] + [
                {"key": "rope_scaffold_vendor", "label": "Existing rope-access or scaffolding contractor on site? (vendor)", "type": "text"},
                {"key": "water_source", "label": "Water source availability (rooftop or ground; potable / recycled)", "type": "textarea"},
                {"key": "wastewater",   "label": "Wastewater capture and drainage arrangements", "type": "textarea"},
            ],
        },
        deepcopy(COMPLIANCE_SECTION),
        deepcopy(FINANCIAL_SECTION),
        deepcopy(DECISION_SECTION),
        deepcopy(NOTES_SECTION),
    ],
}


# -----------------------------------------------------------------
# SERVICE 2: AERIAL IMAGING & INSPECTION
# -----------------------------------------------------------------

AERIAL_IMAGING = {
    "id": "aerial_imaging",
    "name": "Aerial Imaging & Inspection",
    "tagline": "Drone photography, videography, mapping, and visual inspection — mission survey",
    "sections": [
        deepcopy(CONTACT_SECTION),
        {
            "id": "mission_type",
            "title": "Mission Type & Deliverables",
            "fields": [
                {"key": "mission_types", "label": "Type of aerial mission (all that apply)", "type": "multiselect", "required": True,
                 "options": [
                     "Photography (still images)",
                     "Cinematic video / promotional",
                     "Progress documentation (construction)",
                     "Real estate marketing",
                     "Visual inspection (roof, facade, tower, stack)",
                     "Thermal / infrared inspection",
                     "3D mapping / photogrammetry / orthomosaic",
                     "Volumetric survey (stockpile, cut/fill)",
                     "LIDAR scan",
                     "Multispectral (agriculture / vegetation health)",
                     "Emergency / event coverage",
                 ]},
                {"key": "primary_deliverable", "label": "Primary deliverable expected", "type": "textarea", "required": True,
                 "help": "e.g. '50 high-res stills + 90-second edited video', '2D orthomosaic at 3 cm GSD', 'thermal anomaly report'."},
                {"key": "deliverable_format", "label": "Preferred deliverable format(s)", "type": "multiselect",
                 "options": ["JPEG", "RAW/DNG", "MP4 4K", "MP4 1080p", "PDF report", "GeoTIFF orthomosaic", "LAS/LAZ point cloud", "OBJ/PLY 3D model", "KMZ"]},
                {"key": "resolution_gsd", "label": "Required resolution / GSD (ground sample distance)", "type": "text", "help": "e.g. '2 cm/px' for orthomosaic; not needed for cinematic video."},
                {"key": "coverage_hectares", "label": "Approximate coverage area", "type": "number", "unit": "hectares"},
            ],
        },
        {
            "id": "subject",
            "title": "Subject of Inspection / Coverage",
            "fields": [
                {"key": "subject_type", "label": "Subject type", "type": "radio", "required": True,
                 "options": [
                     "Single structure (building, tower, stack)",
                     "Building portfolio / multi-building campus",
                     "Land parcel / development site",
                     "Infrastructure (bridge, road, dam, wind turbine, power line)",
                     "Solar farm / solar array",
                     "Event / crowd",
                     "Other",
                 ]},
                {"key": "subject_description", "label": "Subject description", "type": "textarea", "required": True},
                {"key": "subject_dimensions", "label": "Approximate dimensions (height / length / footprint)", "type": "text"},
                {"key": "inspection_focus",   "label": "Specific defects / features to focus on (cracks, corrosion, hotspots, leaks, missing parts)", "type": "textarea"},
                {"key": "prior_inspections",  "label": "Prior inspection reports available? (attach separately)", "type": "yesno"},
            ],
        },
        {
            "id": "environment",
            "title": "Environment & Flight Conditions",
            "fields": [
                {"key": "environment_type", "label": "Environment", "type": "radio",
                 "options": ["Urban dense", "Urban open", "Suburban", "Industrial site", "Rural / agricultural", "Coastal", "Offshore"]},
                {"key": "gps_denied", "label": "GPS-denied areas expected? (indoor, under bridge, inside enclosure)", "type": "yesno"},
                {"key": "confined_space", "label": "Confined-space or enclosed flight required?", "type": "yesno"},
                {"key": "night_operations", "label": "Night operations required?", "type": "yesno"},
                {"key": "expected_weather", "label": "Expected weather / wind constraints", "type": "textarea"},
            ],
        },
        deepcopy(URGENCY_SECTION),
        deepcopy(ACCESS_SAFETY_SECTION),
        deepcopy(COMPLIANCE_SECTION),
        deepcopy(FINANCIAL_SECTION),
        deepcopy(DECISION_SECTION),
        deepcopy(NOTES_SECTION),
    ],
}


# -----------------------------------------------------------------
# SERVICE 3: ROOF LEAK INSPECTION (thermal / IR-focused)
# -----------------------------------------------------------------

ROOF_LEAK_INSPECTION = {
    "id": "roof_leak_inspection",
    "name": "Roof Leak Inspection (Thermal / IR)",
    "tagline": "Aerial infrared moisture survey and roof leak detection — property survey",
    "sections": [
        deepcopy(CONTACT_SECTION),
        {
            "id": "roof_overview",
            "title": "Roof Overview",
            "fields": [
                {"key": "building_use", "label": "Primary building use", "type": "radio", "required": True,
                 "options": ["Factory / industrial", "Warehouse / logistics", "Office", "Retail / mall", "Hotel", "Residential", "Data center", "Hospital", "Other"]},
                {"key": "roof_area_sqm", "label": "Approximate total roof area", "type": "number", "unit": "sqm", "required": True},
                {"key": "num_roof_sections", "label": "Number of distinct roof sections / elevations", "type": "number"},
                {"key": "building_height_m", "label": "Building height (eave)", "type": "number", "unit": "m", "required": True},
                {"key": "roof_slope", "label": "Roof geometry / slope", "type": "radio",
                 "options": ["Flat / low-slope (≤ 5°)", "Low-slope (5°–15°)", "Pitched (15°–30°)", "Steep (> 30°)", "Mixed"]},
                {"key": "roof_age_years", "label": "Approximate roof age", "type": "number", "unit": "years"},
                {"key": "warranty_status", "label": "Warranty status (in warranty / expired / unknown)", "type": "text"},
            ],
        },
        {
            "id": "roof_construction",
            "title": "Roof Construction",
            "fields": [
                {"key": "roof_membrane", "label": "Roof membrane / covering type", "type": "radio", "required": True,
                 "options": [
                     "Built-up roof (BUR)",
                     "Modified bitumen (mod-bit)",
                     "TPO single-ply",
                     "PVC single-ply",
                     "EPDM (rubber)",
                     "Metal (standing seam / trapezoidal)",
                     "Concrete / cementitious",
                     "Clay or concrete tile",
                     "Asphalt shingle",
                     "Other / mixed",
                 ]},
                {"key": "membrane_notes", "label": "Membrane condition notes (blisters, seam failures, punctures, ponding)", "type": "textarea"},
                {"key": "insulation_type", "label": "Roof insulation type (if known)", "type": "text",
                 "help": "Polyiso, EPS, XPS, mineral wool, spray foam — affects IR interpretation."},
                {"key": "ballasted", "label": "Ballasted roof? (loose stone / pavers over membrane)", "type": "yesno",
                 "help": "Ballast masks thermal signatures — inspection may need debris removal or a different method."},
                {"key": "vegetative_roof", "label": "Green / vegetative roof?", "type": "yesno"},
                {"key": "solar_array_on_roof", "label": "Solar array installed on this roof?", "type": "yesno"},
                {"key": "rooftop_penetrations", "label": "Roof penetrations (HVAC units, skylights, vents, drains, antennas) — count and describe", "type": "textarea"},
                {"key": "parapet_flashing_notes", "label": "Notes on parapet walls, flashings, expansion joints", "type": "textarea"},
            ],
        },
        {
            "id": "leak_history",
            "title": "Leak History & Symptoms",
            "fields": [
                {"key": "leak_reports", "label": "Describe the reported leaks (locations inside the building, when they appeared, weather correlation)", "type": "textarea", "required": True},
                {"key": "num_active_leaks", "label": "Approximate number of active or historical leak locations", "type": "number"},
                {"key": "recent_weather", "label": "Recent weather events (typhoons, prolonged rain, hail)", "type": "textarea"},
                {"key": "prior_repairs", "label": "Prior repair attempts (contractor, date, scope)", "type": "textarea"},
                {"key": "moisture_meter_used", "label": "Has a handheld moisture meter or capacitance meter been used?", "type": "yesno"},
                {"key": "interior_damage", "label": "Interior damage observed (ceiling stains, drywall damage, mold, damaged inventory)", "type": "textarea"},
                {"key": "business_impact", "label": "Business impact (production downtime, damaged goods, safety risk)", "type": "textarea"},
            ],
        },
        {
            "id": "inspection_scope",
            "title": "Inspection Scope & Method",
            "fields": [
                {"key": "inspection_types", "label": "Types of inspection requested", "type": "multiselect", "required": True,
                 "options": [
                     "Aerial thermal / infrared moisture survey (drone)",
                     "Aerial visual / RGB roof condition survey",
                     "Rooftop walk-over with handheld thermal camera",
                     "Moisture meter verification of IR anomalies",
                     "Core sampling (destructive) of suspect areas",
                     "Nuclear / capacitance moisture scan",
                     "Post-repair verification survey",
                 ]},
                {"key": "moisture_mapping", "label": "Moisture map deliverable required?", "type": "yesno",
                 "help": "Scaled roof map with wet areas outlined in colour, matched to marked areas on the physical roof."},
                {"key": "verification_marking", "label": "On-roof marking of anomalies (spray paint / flags)?", "type": "yesno"},
                {"key": "budget_repair_estimate", "label": "Do you also want a rough repair-cost estimate in the report?", "type": "yesno"},
                {"key": "certified_thermographer_required", "label": "Level II or III certified thermographer required?", "type": "yesno",
                 "help": "Some warranties or facilities require ITC / Infraspection Level II or III certification on the report."},
            ],
        },
        {
            "id": "site_conditions",
            "title": "Site Conditions for IR Flight",
            "description": "Infrared roof surveys are typically flown around sunset after a clear, dry day so the roof has absorbed solar energy and wet zones cool more slowly than dry ones.",
            "fields": [
                {"key": "preferred_flight_window", "label": "Preferred flight window", "type": "radio",
                 "options": [
                     "Sunset / dusk (industry standard for IR moisture)",
                     "Night (2–4 h after sunset)",
                     "Daytime (visual only)",
                     "No preference — Skyline to advise",
                 ]},
                {"key": "roof_dry_48h", "label": "Has the roof been dry for at least 24-48 hours before the planned inspection?", "type": "yesno"},
                {"key": "wind_conditions", "label": "Typical wind at rooftop level (kph, if known)", "type": "text"},
                {"key": "night_lighting", "label": "Rooftop lighting available for verification walk-through after IR flight?", "type": "yesno"},
                {"key": "roof_walkable", "label": "Is the roof safely walkable for a follow-up moisture-meter check?", "type": "yesno"},
                {"key": "fall_protection", "label": "Fall-protection anchor points available for walk-over?", "type": "yesno"},
            ],
        },
        deepcopy(URGENCY_SECTION),
        deepcopy(ACCESS_SAFETY_SECTION),
        deepcopy(COMPLIANCE_SECTION),
        deepcopy(FINANCIAL_SECTION),
        deepcopy(DECISION_SECTION),
        deepcopy(NOTES_SECTION),
    ],
}


# -----------------------------------------------------------------
# SERVICE 4: FIREFIGHTING EQUIPMENT (drone-based aerial firefighting support / equipment demo)
# -----------------------------------------------------------------

FIREFIGHTING_EQUIPMENT = {
    "id": "firefighting_equipment",
    "name": "Firefighting Equipment",
    "tagline": "Drone-based aerial firefighting equipment survey and deployment plan",
    "sections": [
        deepcopy(CONTACT_SECTION),
        {
            "id": "facility",
            "title": "Facility & Fire Risk Profile",
            "fields": [
                {"key": "facility_type", "label": "Facility type", "type": "radio", "required": True,
                 "options": [
                     "High-rise office / residential tower",
                     "Industrial / manufacturing plant",
                     "Petrochemical / oil & gas",
                     "Warehouse / logistics",
                     "Data center",
                     "Airport / aviation",
                     "Port / marine terminal",
                     "Utility (power plant, substation)",
                     "Hospital / healthcare",
                     "Public infrastructure",
                     "Wildland-urban interface",
                 ]},
                {"key": "primary_fire_hazards", "label": "Primary fire hazards on site (all that apply)", "type": "multiselect",
                 "options": [
                     "Flammable liquids", "Flammable gases", "Combustible dust",
                     "Lithium-ion batteries", "High-voltage electrical",
                     "Class A ordinary combustibles", "Chemicals / hazardous materials",
                     "Confined-space fires", "High-piled storage",
                 ]},
                {"key": "hazmat_present", "label": "Hazardous materials on site? (list types and locations)", "type": "textarea"},
                {"key": "occupancy_load",  "label": "Typical occupancy load (people on site)", "type": "number"},
                {"key": "site_size_sqm",   "label": "Approximate site size", "type": "number", "unit": "sqm"},
                {"key": "tallest_structure_m", "label": "Tallest structure height", "type": "number", "unit": "m"},
                {"key": "high_reach_needed", "label": "High-reach access required beyond ladder truck (> 30 m)?", "type": "yesno"},
            ],
        },
        {
            "id": "current_systems",
            "title": "Current Firefighting Systems",
            "fields": [
                {"key": "existing_systems", "label": "Existing fire protection systems (all that apply)", "type": "multiselect",
                 "options": [
                     "Wet sprinkler", "Dry sprinkler", "Deluge system", "Foam suppression",
                     "Clean-agent gas (FM-200 / Novec / Inergen)", "CO₂ system",
                     "Standpipes / hydrants", "Water tanks / reservoirs",
                     "Fire pump station", "Smoke management",
                     "Fire alarm / detection (addressable / conventional)",
                     "None",
                 ]},
                {"key": "response_capability", "label": "On-site emergency response capability", "type": "radio",
                 "options": ["Trained fire brigade on shift", "Emergency response team (part-time)", "External BFP / mutual aid only", "None"]},
                {"key": "nearest_fire_station_km", "label": "Distance to nearest fire station", "type": "number", "unit": "km"},
                {"key": "average_response_time_min", "label": "Typical fire-service response time", "type": "number", "unit": "min"},
                {"key": "recent_incidents", "label": "Recent fire incidents or near-misses (last 3 years)", "type": "textarea"},
            ],
        },
        {
            "id": "drone_scope",
            "title": "Drone Firefighting Scope",
            "fields": [
                {"key": "drone_use_cases", "label": "Intended drone firefighting use cases", "type": "multiselect", "required": True,
                 "options": [
                     "Aerial reconnaissance / situational awareness",
                     "Thermal hotspot detection during and after fire",
                     "Search and rescue in smoke-obscured areas",
                     "Delivery of fire extinguishing balls / capsules",
                     "High-rise window-breach / suppression drone",
                     "Payload dropping (foam, dry chemical, water)",
                     "Communications relay for responders",
                     "Post-incident damage assessment",
                     "Training / drill support",
                 ]},
                {"key": "engagement_type", "label": "Engagement type", "type": "radio", "required": True,
                 "options": [
                     "Standby retainer (on-call response)",
                     "On-site stationed equipment + trained pilot(s)",
                     "Equipment purchase + operator training",
                     "One-time drill / demo",
                     "Consulting / feasibility study only",
                 ]},
                {"key": "response_time_target", "label": "Required response time from call to on-scene", "type": "text", "help": "e.g. 'within 5 min for on-site retainer', 'within 30 min metro area'."},
                {"key": "coverage_area", "label": "Coverage area (single site, multi-site portfolio, city)", "type": "text"},
                {"key": "24_7_required", "label": "24/7 availability required?", "type": "yesno"},
            ],
        },
        {
            "id": "regulatory",
            "title": "Regulatory & Coordination",
            "fields": [
                {"key": "bfp_coordination", "label": "Bureau of Fire Protection (BFP) coordination on file?", "type": "yesno"},
                {"key": "caap_special_ops", "label": "CAAP special-operations approval for emergency flights?", "type": "yesno"},
                {"key": "insurer_notified", "label": "Property insurer notified / requires notification?", "type": "yesno"},
                {"key": "existing_erp",     "label": "Existing Emergency Response Plan (ERP) to integrate with? (attach if available)", "type": "yesno"},
                {"key": "training_required","label": "In-house team training required?", "type": "yesno"},
                {"key": "training_seats",   "label": "Number of personnel to train (if applicable)", "type": "number"},
            ],
        },
        deepcopy(URGENCY_SECTION),
        deepcopy(ACCESS_SAFETY_SECTION),
        deepcopy(COMPLIANCE_SECTION),
        deepcopy(FINANCIAL_SECTION),
        deepcopy(DECISION_SECTION),
        deepcopy(NOTES_SECTION),
    ],
}


SERVICES = [FACADE_CLEANING, AERIAL_IMAGING, ROOF_LEAK_INSPECTION, FIREFIGHTING_EQUIPMENT]
SERVICE_BY_ID = {s["id"]: s for s in SERVICES}


def service_summary():
    """Compact list for the service picker."""
    return [{"id": s["id"], "name": s["name"], "tagline": s["tagline"]} for s in SERVICES]
