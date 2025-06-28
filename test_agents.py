from src.code_review.agents import NamingAgent, SyntaxAgent, LogicAgent, SummaryAgent
from src.code_review.pipeline.workflow import run_pipeline

def test_individual_agents():
    """Test each agent individually."""
    print("Testing Individual Agents")
    print("-" * 30)
    
    # Test data
    sample_declarations = [
        {"name": "calculate_total_price", "line": 5},
        {"name": "x", "line": 10},
        {"name": "isValid", "line": 15}
    ]
    
    sample_code = """
def calculate_total_price(items):
    total = 0
    for item in items:
        total += item.price
    return total

x = 5  # unclear variable name
isValid = True  # should be is_valid in Python
"""
    
    # NamingAgent
    print("\n1. Testing NamingAgent...")
    naming_agent = NamingAgent()
    naming_result = naming_agent.process(sample_declarations)
    print(f"   Result: {naming_result}")
    
    # SyntaxAgent
    print("\n2. Testing SyntaxAgent...")
    syntax_agent = SyntaxAgent()
    syntax_result = syntax_agent.process(sample_code, "python")
    print(f"   Result: {syntax_result}")
    
    # LogicAgent
    print("\n3. Testing LogicAgent...")
    logic_agent = LogicAgent()
    logic_result = logic_agent.process(sample_code, [])
    print(f"   Result: {logic_result}")
    
    # SummaryAgent
    print("\n4. Testing SummaryAgent...")
    summary_agent = SummaryAgent()
    feedbacks = [naming_result, syntax_result, logic_result]
    summary_result = summary_agent.process(sample_code, feedbacks)
    print(f"   Result: {summary_result}")
    
    print("\nIndividual agent tests completed!")

def test_complete_pipeline():
    """Test the complete pipeline."""
    print("\n\nTesting Complete Pipeline")
    print("=" * 50)
    
    sample_diff = """
diff --git a/example.py b/example.py
index abc123..def456 100644
--- a/example.py
+++ b/example.py
@@ -1,5 +1,8 @@
 def calculate_total_price(items):
     total = 0
     for item in items:
-        total += item.price
+        total += item.price * 1.1  # add 10% tax
     return total
+
+x = 5  # unclear variable name
+isValid = True  # should be is_valid
"""
    
    try:
        result = run_pipeline(sample_diff)
        print("\nPipeline Results:")
        print("-" * 30)
        
        for key, value in result.items():
            print(f"{key}: {value}")
            
        print("\nComplete pipeline test completed!")
        return True
        
    except Exception as e:
        print(f"\nPipeline test failed: {str(e)}")
        return False

def main():
    """Main test function."""
    print("Starting Agent Architecture Tests")
    print("=" * 60)
    
    try:
        test_individual_agents()
        success = test_complete_pipeline()
        
        if success:
            print("\nAll tests passed!")
        else:
            print("\n Some tests failed. Please check the error messages above.")
            
    except Exception as e:
        print(f"\nTest suite failed with error: {str(e)}")
        print("Make sure the model file is available and all dependencies are installed.")

if __name__ == "__main__":
    main()
