import streamlit as st
from dotenv import load_dotenv
from code_review_agent.code_review_agent import run_pipeline

# Load environment variables
load_dotenv(".env")

def main():
    """Main entry point"""
    st.set_page_config(
        page_title="Bot Review Assistant",
        page_icon="🙈",
        layout="wide"
    )

    st.title("🙈 Bot Review Assistant")
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.header("Instructions")
        st.markdown("""
            1. **Paste your PR diff** in the text area
            2. **Click 'Review Code'** to start analysis
            3. **View results** including:
               - Language detection
               - Code structure scan
               - Naming conventions
               - Syntax validation
               - Logic review
               - Summary
            """)

        st.header("Example Diff Format")
        st.code("""
diff --git a/example.py b/example.py
index abc123..def456 100644
--- a/example.py
+++ b/example.py
@@ -1,3 +1,4 @@
 def add(a, b):
-    return a + b
+    return a + b + 0  # ensure result is int
        """
                , language="diff")

    # Main content area
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("Input")
        diff_input = st.text_area(
            "Paste your PR diff here:",
            height=400,
            placeholder="Paste your git diff output here..."
        )

        review_button = st.button("Review Code", type="primary", use_container_width=True)

    with col2:
        st.header("Results")

        if review_button:
            if diff_input.strip():
                with st.spinner("Analyzing code... This may take a moment."):
                    try:
                        result = run_pipeline(diff_input)
                        print(result)

                        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                            "Summary", "Language", "Structure",
                            "Naming", "Syntax", "Logic"
                        ])

                        with tab1:
                            if "summary" in result:
                                st.success("Analysis Complete")
                                st.write(result["summary"])
                            else:
                                st.warning("No summary available")

                        with tab2:
                            if "language" in result:
                                st.info(f"Detected Language: **{result['language']}**")
                            else:
                                st.warning("Language detection failed")

                        with tab3:
                            if "scan" in result and result["scan"]:
                                st.success(f"Found {len(result['scan'])} code structures")
                                for item in result["scan"]:
                                    st.write(f"- **{item['name']}** (line {item['line']})")
                            else:
                                st.info("No code structures detected")

                        with tab4:
                            if "naming" in result:
                                naming = result["naming"]
                                if naming.get("lines"):
                                    st.warning("Naming Issues Found")
                                    for issue in naming["lines"]:
                                        st.write(f"Line {issue['line']}: {issue['feedback']}")
                                else:
                                    st.success("No naming issues found")
                                st.write(f"**Summary:** {naming.get('summary', 'N/A')}")
                            else:
                                st.warning("Naming check failed")

                        with tab5:
                            if "syntax" in result:
                                syntax = result["syntax"]
                                if syntax.get("valid", True):
                                    st.success("Syntax is valid")
                                else:
                                    st.error("Syntax errors found")
                                    for issue in syntax.get("lines", []):
                                        st.write(f"Line {issue['line']}: {issue['feedback']}")
                                st.write(f"**Summary:** {syntax.get('summary', 'N/A')}")
                            else:
                                st.warning("Syntax check failed")

                        with tab6:
                            if "review" in result:
                                review = result["review"]
                                if review.get("lines"):
                                    st.warning("Logic Issues Found")
                                    for issue in review["lines"]:
                                        st.write(f"Line {issue['line']}: {issue['feedback']}")
                                else:
                                    st.success("No logic issues found")
                                st.write(f"**Summary:** {review.get('summary', 'N/A')}")
                            else:
                                st.warning("Logic review failed")

                        # Raw JSON
                        with st.expander("Raw JSON Output"):
                            st.json(result)

                    except Exception as e:
                        st.error(f"Error during analysis: {str(e)}")
                        st.info("Make sure your model file is in the correct location and try again.")
            else:
                st.error("Please provide a diff to review")

if __name__ == "__main__":
    main()