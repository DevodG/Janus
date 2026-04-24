"""
Test script to verify all requirements for Task 7 are met.

Requirements being tested:
- 4.1: Switchboard classifies using four dimensions (task_family, domain_pack, complexity, execution_mode)
- 4.2: Simple queries (≤5 words) route to solo mode
- 4.3: Medium queries (≤25 words) route to standard mode
- 4.4: Complex queries (>25 words) route to deep mode
- 4.5: Simulation trigger keywords detected
- 4.6: Keywords are environment-configurable
- 4.7: task_family="simulation" when keywords detected
- 5.6: Domain pack detection using domain registry
"""

from app.agents.switchboard import decide_route
from app.domain_packs.init_packs import init_domain_packs
from app.domain_packs.registry import get_registry
from app.config import SIMULATION_TRIGGER_KEYWORDS


def test_requirement_4_1():
    """Test Requirement 4.1: Four-dimension classification"""
    print("\n" + "="*60)
    print("Testing Requirement 4.1: Four-dimension classification")
    print("="*60)
    
    init_domain_packs()
    
    result = decide_route("What is the stock market doing today?")
    
    required_keys = ["task_family", "domain_pack", "complexity", "execution_mode"]
    
    for key in required_keys:
        if key in result:
            print(f"✅ {key}: {result[key]}")
        else:
            print(f"❌ Missing dimension: {key}")
            return False
    
    print("✅ Requirement 4.1 PASSED: All four dimensions present")
    return True


def test_requirement_4_2():
    """Test Requirement 4.2: Simple queries (≤5 words) route to solo mode"""
    print("\n" + "="*60)
    print("Testing Requirement 4.2: Simple queries route to solo mode")
    print("="*60)
    
    init_domain_packs()
    
    test_cases = [
        "Hello",
        "Hi there",
        "What is this?",
        "Tell me more",
        "Show me data",
    ]
    
    all_passed = True
    for query in test_cases:
        result = decide_route(query)
        word_count = len(query.split())
        
        if word_count <= 5:
            if result["complexity"] == "simple" and result["execution_mode"] == "solo":
                print(f"✅ '{query}' ({word_count} words) -> solo mode")
            else:
                print(f"❌ '{query}' ({word_count} words) -> {result['execution_mode']} (expected solo)")
                all_passed = False
    
    if all_passed:
        print("✅ Requirement 4.2 PASSED")
    return all_passed


def test_requirement_4_3():
    """Test Requirement 4.3: Medium queries (≤25 words) route to standard mode"""
    print("\n" + "="*60)
    print("Testing Requirement 4.3: Medium queries route to standard mode")
    print("="*60)
    
    init_domain_packs()
    
    test_cases = [
        "Can you tell me about the weather today?",
        "What are the latest developments in artificial intelligence and machine learning?",
        "I would like to know more about the current economic situation in the United States.",
    ]
    
    all_passed = True
    for query in test_cases:
        result = decide_route(query)
        word_count = len(query.split())
        
        if 5 < word_count <= 25:
            if result["complexity"] == "medium" and result["execution_mode"] == "standard":
                print(f"✅ '{query[:50]}...' ({word_count} words) -> standard mode")
            else:
                print(f"❌ '{query[:50]}...' ({word_count} words) -> {result['execution_mode']} (expected standard)")
                all_passed = False
    
    if all_passed:
        print("✅ Requirement 4.3 PASSED")
    return all_passed


def test_requirement_4_4():
    """Test Requirement 4.4: Complex queries (>25 words) route to deep mode"""
    print("\n" + "="*60)
    print("Testing Requirement 4.4: Complex queries route to deep mode")
    print("="*60)
    
    init_domain_packs()
    
    query = "I need a comprehensive analysis of the current market conditions including economic indicators, sector performance, and potential risks that could impact my investment portfolio over the next quarter with detailed recommendations."
    
    result = decide_route(query)
    word_count = len(query.split())
    
    if word_count > 25:
        if result["complexity"] == "complex" and result["execution_mode"] == "deep":
            print(f"✅ Query ({word_count} words) -> deep mode")
            print("✅ Requirement 4.4 PASSED")
            return True
        else:
            print(f"❌ Query ({word_count} words) -> {result['execution_mode']} (expected deep)")
            return False
    else:
        print(f"❌ Test query has only {word_count} words (need >25)")
        return False


def test_requirement_4_5_and_4_7():
    """Test Requirements 4.5 & 4.7: Simulation keyword detection and task_family setting"""
    print("\n" + "="*60)
    print("Testing Requirements 4.5 & 4.7: Simulation keyword detection")
    print("="*60)
    
    init_domain_packs()
    
    # Test with various simulation keywords
    test_cases = [
        "simulate the market reaction",
        "predict the outcome",
        "what if scenario analysis",
        "model the reaction",
        "test different scenarios",
    ]
    
    all_passed = True
    for query in test_cases:
        result = decide_route(query)
        
        if result["task_family"] == "simulation":
            print(f"✅ '{query}' -> task_family=simulation")
        else:
            print(f"❌ '{query}' -> task_family={result['task_family']} (expected simulation)")
            all_passed = False
    
    if all_passed:
        print("✅ Requirements 4.5 & 4.7 PASSED")
    return all_passed


def test_requirement_4_6():
    """Test Requirement 4.6: Keywords are environment-configurable"""
    print("\n" + "="*60)
    print("Testing Requirement 4.6: Keywords are environment-configurable")
    print("="*60)
    
    # Check that keywords are loaded from config
    if SIMULATION_TRIGGER_KEYWORDS:
        print(f"✅ Simulation keywords loaded from config: {len(SIMULATION_TRIGGER_KEYWORDS)} keywords")
        print(f"   Sample keywords: {SIMULATION_TRIGGER_KEYWORDS[:5]}")
        print("✅ Requirement 4.6 PASSED")
        return True
    else:
        print("❌ No simulation keywords found in config")
        return False


def test_requirement_5_6():
    """Test Requirement 5.6: Domain pack detection using domain registry"""
    print("\n" + "="*60)
    print("Testing Requirement 5.6: Domain pack detection")
    print("="*60)
    
    init_domain_packs()
    registry = get_registry()
    
    # Test finance domain detection
    test_cases = [
        ("What is the stock market doing?", "finance"),
        ("Tell me about NASDAQ", "finance"),
        ("How is the weather?", "general"),
        ("What are earnings reports?", "finance"),
    ]
    
    all_passed = True
    for query, expected_domain in test_cases:
        result = decide_route(query)
        detected = result["domain_pack"]
        
        if detected == expected_domain:
            print(f"✅ '{query}' -> domain={detected}")
        else:
            print(f"❌ '{query}' -> domain={detected} (expected {expected_domain})")
            all_passed = False
    
    if all_passed:
        print("✅ Requirement 5.6 PASSED")
    return all_passed


def run_all_tests():
    """Run all requirement tests"""
    print("\n" + "="*60)
    print("TASK 7 REQUIREMENTS VERIFICATION")
    print("="*60)
    
    tests = [
        ("4.1", test_requirement_4_1),
        ("4.2", test_requirement_4_2),
        ("4.3", test_requirement_4_3),
        ("4.4", test_requirement_4_4),
        ("4.5 & 4.7", test_requirement_4_5_and_4_7),
        ("4.6", test_requirement_4_6),
        ("5.6", test_requirement_5_6),
    ]
    
    results = {}
    for req_id, test_func in tests:
        try:
            results[req_id] = test_func()
        except Exception as e:
            print(f"\n❌ Requirement {req_id} FAILED with exception: {e}")
            results[req_id] = False
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for req_id, passed_test in results.items():
        status = "✅ PASSED" if passed_test else "❌ FAILED"
        print(f"Requirement {req_id}: {status}")
    
    print(f"\nTotal: {passed}/{total} requirements passed")
    
    return all(results.values())


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
