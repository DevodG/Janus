"""
Test script for switchboard routing enhancements.
"""

from app.agents.switchboard import decide_route
from app.domain_packs.init_packs import init_domain_packs


def test_routing():
    """Test the enhanced switchboard routing."""
    
    # Initialize domain packs
    init_domain_packs()
    
    # Test cases
    test_cases = [
        # Simple queries (≤5 words)
        {
            "input": "Hello world",
            "expected": {
                "complexity": "simple",
                "execution_mode": "solo",
                "task_family": "normal",
                "domain_pack": "general"
            }
        },
        {
            "input": "What is AAPL?",
            "expected": {
                "complexity": "simple",
                "execution_mode": "solo",
                "task_family": "normal",
                "domain_pack": "general"  # AAPL alone doesn't trigger finance keywords
            }
        },
        
        # Medium queries (≤25 words)
        {
            "input": "Can you tell me about the latest stock market trends and what's happening with tech stocks?",
            "expected": {
                "complexity": "medium",
                "execution_mode": "standard",
                "task_family": "normal",
                "domain_pack": "finance"
            }
        },
        {
            "input": "What are the best practices for software development in modern teams?",
            "expected": {
                "complexity": "medium",
                "execution_mode": "standard",
                "task_family": "normal",
                "domain_pack": "general"
            }
        },
        
        # Complex queries (>25 words)
        {
            "input": "I need a comprehensive analysis of the current market conditions including economic indicators, sector performance, and potential risks that could impact my investment portfolio over the next quarter.",
            "expected": {
                "complexity": "complex",
                "execution_mode": "deep",
                "task_family": "normal",
                "domain_pack": "finance"
            }
        },
        
        # Simulation queries
        {
            "input": "Simulate the market reaction to a Fed rate hike",
            "expected": {
                "complexity": "complex",
                "execution_mode": "deep",
                "task_family": "simulation",
                "domain_pack": "finance"
            }
        },
        {
            "input": "What if the company announces bankruptcy?",
            "expected": {
                "complexity": "complex",
                "execution_mode": "deep",
                "task_family": "simulation",
                "domain_pack": "finance"  # "bankruptcy" is a finance keyword
            }
        },
    ]
    
    print("Testing Switchboard Routing\n" + "="*50)
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        user_input = test["input"]
        expected = test["expected"]
        
        result = decide_route(user_input)
        
        print(f"\nTest {i}:")
        print(f"  Input: {user_input}")
        print(f"  Result: {result}")
        
        # Check each expected field
        test_passed = True
        for key, expected_value in expected.items():
            if result.get(key) != expected_value:
                print(f"  ❌ FAILED: {key} = {result.get(key)}, expected {expected_value}")
                test_passed = False
        
        if test_passed:
            print(f"  ✅ PASSED")
            passed += 1
        else:
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    
    return failed == 0


if __name__ == "__main__":
    success = test_routing()
    exit(0 if success else 1)
