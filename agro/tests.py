from django.test import TestCase
from django.contrib.auth.models import User
from .services.language_detector import detect_language
from .services.yield_prediction import calculate_yield_and_profit
from .services.scheme_matcher import calculate_eligibility_scores
from .models import YieldPredictionHistory, FavoriteScheme, GovernmentScheme

class AgroSathiServicesTestCase(TestCase):
    
    def test_language_detection(self):
        """Test Unicode script language detection."""
        # Kannada
        kn_res = detect_language("ನಮಸ್ಕಾರ")
        self.assertEqual(kn_res['code'], 'kn')
        self.assertEqual(kn_res['language'], 'Kannada')
        
        # Telugu
        te_res = detect_language("నమస్కారం")
        self.assertEqual(te_res['code'], 'te')
        self.assertEqual(te_res['language'], 'Telugu')
        
        # English
        en_res = detect_language("How to irrigate rice fields?")
        self.assertEqual(en_res['code'], 'en')
        self.assertEqual(en_res['language'], 'English')

    def test_yield_and_profit_prediction(self):
        """Test yield calculation multipliers and output calculations."""
        inputs = {
            'crop_type': 'Wheat',
            'farm_size': 2.0,
            'soil_type': 'loamy',
            'season': 'winter',
            'rainfall': 400.0,
            'temperature': 22.0,
            'seed_cost': 2000,
            'fertilizer_cost': 3000,
            'labor_cost': 4000
        }
        outputs = calculate_yield_and_profit(inputs)
        
        # Total cost check: 2000 + 3000 + 4000 = 9000
        self.assertEqual(outputs['estimated_expenses'], 9000.0)
        # Expected yield must be positive
        self.assertGreater(outputs['expected_yield'], 0)
        # Estimated revenue must be positive
        self.assertGreater(outputs['estimated_revenue'], 0)
        
    def test_scheme_matching_eligibility(self):
        """Test scheme eligibility matcher rules."""
        # Setup dummy GovernmentScheme
        s = GovernmentScheme.objects.create(
            scheme_id="test-pmksy",
            title="Pradhan Mantri Krishi Sinchayee Yojana (PMKSY) - Test",
            short_description="Irrigation support",
            description="Irrigation support test scheme",
            category="irrigation",
            states=["Maharashtra", "Rajasthan"],
            eligibility="Dryland/Rainfed and small farmers",
            benefits="Subsidy on micro-irrigation systems",
            apply_url="https://pmksy.gov.in"
        )
        
        inputs = {
            'state': 'Maharashtra',
            'category': 'small_marginal',
            'land_holding_size': 2.5,
            'crop_type': 'Wheat',
            'irrigation_availability': 'no'
        }
        
        results = calculate_eligibility_scores(inputs)
        matched = [r for r in results if r['scheme_id'] == 'test-pmksy']
        
        # Verify scheme is matched and score is high (due to state, category, and lack of irrigation)
        self.assertEqual(len(matched), 1)
        self.assertGreaterEqual(matched[0]['eligibility_score'], 80)

    def test_disease_detection_image_validation(self):
        """Test leaf validation heuristics on synthetic images."""
        from .services.disease import _check_leaf_with_cv
        from PIL import Image
        import io

        # 1. Create a synthetic green/brown "leaf-like" image (should pass CV check)
        img_green = Image.new('RGB', (128, 128), color=(34, 139, 34))  # Forest Green
        buf_green = io.BytesIO()
        img_green.save(buf_green, format='JPEG')
        green_bytes = buf_green.getvalue()

        self.assertTrue(_check_leaf_with_cv(green_bytes))

        # 2. Create a synthetic document/screenshot image (mostly white background - should fail)
        img_white = Image.new('RGB', (128, 128), color=(255, 255, 255))
        buf_white = io.BytesIO()
        img_white.save(buf_white, format='JPEG')
        white_bytes = buf_white.getvalue()

        self.assertFalse(_check_leaf_with_cv(white_bytes))

        # 3. Create a synthetic dark-mode screenshot / dark image (mostly black background - should fail)
        img_black = Image.new('RGB', (128, 128), color=(5, 5, 5))
        buf_black = io.BytesIO()
        img_black.save(buf_black, format='JPEG')
        black_bytes = buf_black.getvalue()

        self.assertFalse(_check_leaf_with_cv(black_bytes))

        # 4. Create a synthetic non-leaf colored image (e.g. blue image - should fail)
        img_blue = Image.new('RGB', (128, 128), color=(20, 40, 200))
        buf_blue = io.BytesIO()
        img_blue.save(buf_blue, format='JPEG')
        blue_bytes = buf_blue.getvalue()

        self.assertFalse(_check_leaf_with_cv(blue_bytes))

