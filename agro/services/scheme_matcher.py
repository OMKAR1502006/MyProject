from typing import List, Dict, Any
from agro.models import GovernmentScheme
from agro.services.schemes import ensure_schemes_in_db

def calculate_eligibility_scores(inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Evaluates government schemes and computes eligibility scores (0-100%)
    based on farmer criteria: state, category, land_holding_size, crop_type, irrigation.
    """
    ensure_schemes_in_db()
    
    state = (inputs.get('state') or 'All').strip().lower()
    category = (inputs.get('category') or 'all').strip().lower()
    
    try:
        land_size = float(inputs.get('land_holding_size') or 0.0)
    except (ValueError, TypeError):
        land_size = 0.0
        
    crop = (inputs.get('crop_type') or '').strip().lower()
    irrigation = (inputs.get('irrigation_availability') or 'yes').strip().lower()

    schemes = GovernmentScheme.objects.filter(is_active=True)
    results = []

    for s in schemes:
        score = 80  # Base score for active schemes

        # 1. State Check (strict check)
        states_list = [x.lower() for x in (s.states or ['all'])]
        if 'all' not in states_list and 'all' not in state:
            if state not in states_list:
                # Ineligible due to state residency constraints
                continue

        # 2. Category Check
        # Categories: general, income_support, insurance, credit, soil, irrigation, organic, subsidy, horticulture, climate, state
        scheme_category = (s.category or '').lower()
        if category != 'all' and category != 'general':
            if category in scheme_category or scheme_category in category:
                score += 15
            else:
                score -= 10

        # 3. Land holding size constraints
        eligibility_text = (s.eligibility or '').lower()
        desc_text = (s.description or '').lower()
        title_text = (s.title or '').lower()

        is_small_marginal_only = (
            "small and marginal" in eligibility_text 
            or "small & marginal" in eligibility_text
            or "marginal farmer" in eligibility_text
            or "landholding limit" in eligibility_text
        )

        if is_small_marginal_only:
            if land_size > 5.0:  # > 5 acres / 2 hectares is general/large farmer in India
                score -= 40
            else:
                score += 15

        # 4. Crop type matching
        if crop:
            is_horticulture_scheme = (
                "horticulture" in eligibility_text 
                or "horticulture" in desc_text 
                or "horticulture" in title_text
                or "fruits" in eligibility_text
                or "vegetables" in eligibility_text
            )
            horticulture_crops = ['onion', 'tomato', 'potato', 'chili', 'fruits', 'vegetables', 'mango', 'banana']
            
            if is_horticulture_scheme:
                if crop in horticulture_crops:
                    score += 20
                else:
                    score -= 30  # heavily penalty for growing standard grains on horticulture scheme
            elif "organic" in title_text or "organic" in desc_text:
                if crop in ['cotton', 'soybean', 'pulses', 'maize']:
                    score += 10
            elif "cotton" in title_text or "cotton" in desc_text:
                if crop == 'cotton':
                    score += 25
                else:
                    score -= 30

        # 5. Irrigation matching
        # PMKSY (Sinchayee) represents water and irrigation
        is_irrigation_scheme = (
            "sinchayee" in title_text 
            or "sinchayee" in desc_text 
            or "irrigation" in eligibility_text 
            or "irrigation" in desc_text
            or "water harvesting" in desc_text
        )
        if is_irrigation_scheme:
            if irrigation == 'no':
                score += 20  # highly eligible if they don't have irrigation yet!
            else:
                score += 5   # still eligible but neutral

        # Bound score between 10% and 100%
        final_score = max(10, min(100, score))

        results.append({
            'scheme_id': s.scheme_id,
            'title': s.title,
            'short_description': s.short_description,
            'description': s.description,
            'category': s.category,
            'states': s.states,
            'eligibility': s.eligibility,
            'benefits': s.benefits,
            'application_steps': s.application_steps,
            'apply_url': s.apply_url,
            'eligibility_score': final_score,
        })

    # Sort results by eligibility score descending
    results.sort(key=lambda x: x['eligibility_score'], reverse=True)
    return results
