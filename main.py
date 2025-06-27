import streamlit as st
from dotenv import load_dotenv

from example import example_diff, example_custom_bitbucket_diff
from src.code_review.pipeline.workflow import run_pipeline

# Load environment variables
load_dotenv(".env")

def main():
    """Main entry point"""
    st.set_page_config(
        page_title="Code Review Assistant",
        page_icon="🙈",
        layout="wide"
    )

    st.title("🙈 Code Review Assistant")
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.header("Instructions")
        st.markdown("""
            1. **Paste your PR diff** in the text area
            2. **Click 'Review Code'** to start analysis
            3. **View results** including:
               - Code structure scan
               - Naming conventions
               - Syntax validation
               - Logic review
               - Summary
            """)

        st.header("Example Diff Format")
        st.code(example_custom_bitbucket_diff, language="diff")

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
                        print("\n\n")
                        print(result.get("review_result", {}))

                        summary_result = result.get("summary_result", {})
                        summary_dict = summary_result.get("summary", {})
                        summary = summary_dict.get("summary", "[No business summary]")
                        technical_details = summary_dict.get("technical_details", "[No technical details]")
                        review_result = result.get("review_result", {})
                        file_reviews = review_result.get("file_reviews", [])
                        total_files_reviewed = review_result.get("total_files_reviewed", 0)
                        total_chunks_reviewed = review_result.get("total_chunks_reviewed", 0)

                        review = result.get("review_result", {})
                        review_error = review.get("error", None)

                        def display_field(field, label):
                            if isinstance(field, list):
                                if not field:
                                    st.write(f"[No {label}]")
                                elif len(field) == 1:
                                    st.write(field[0])
                                else:
                                    st.write(f"{label.capitalize()} (per file/chunk):")
                                    for idx, item in enumerate(field, 1):
                                        st.write(f"{idx}. {item}")
                            else:
                                st.write(field if field else f"[No {label}]")

                        tab1, tab2 = st.tabs(["Summary", "Review"])

                        with tab1:
                            st.subheader("Business Summary")
                            st.write(summary)
                            st.subheader("Technical Details")
                            st.write(technical_details)

                        with tab2:
                            if review_error:
                                st.error(f"Review error: {review_error}")
                            if not file_reviews:
                                st.info("No file reviews available.")
                            else:
                                for file_obj in file_reviews:
                                    st.markdown(f"### File: `{file_obj.get('file_path', '[unknown]')}`")
                                    st.markdown(f"**Diff lines:** {file_obj.get('diff_lines', [])}")
                                    st.subheader("Line-by-line Feedback")
                                    lf = file_obj.get("line_feedback", [])
                                    if isinstance(lf, dict):
                                        lf = [{k: v} for k, v in lf.items()]
                                    if not lf:
                                        st.write("[No line feedback]")
                                    else:
                                        for fb in lf:
                                            for line, comment in fb.items():
                                                st.markdown(f"**Line {line}:**")
                                                if isinstance(comment, dict):
                                                    if 'comment' in comment:
                                                        st.write(comment['comment'])
                                                    
                                                    # Display matched best practices and severity
                                                    if 'matched_best_practices_and_severities' in comment and comment['matched_best_practices_and_severities']:
                                                        st.markdown("**Matched Best Practices:**")
                                                        for bp_item in comment['matched_best_practices_and_severities']:
                                                            st.markdown(f"- {bp_item}")
                                                    
                                                    for k in ['suggest_code', 'explain_suggest_code']:
                                                        if k in comment:
                                                            if k == 'suggest_code':
                                                                st.markdown(comment[k])
                                                            else:
                                                                st.write(comment[k])
                                                    if not any(x in comment for x in ['comment', 'suggest_code', 'explain_suggest_code', 'matched_best_practices_and_severities']):
                                                        st.write(comment)
                                    st.subheader("Key Issues to Review")
                                    st.write(file_obj.get("key_issues_to_review", []))
                                    st.subheader("Security Concerns")
                                    display_field(file_obj.get("security_concerns", []), "security concerns")
                                    st.subheader("Relevant Tests")
                                    relevant_tests = file_obj.get("relevant_tests", [])
                                    if relevant_tests and isinstance(relevant_tests, list) and len(relevant_tests) > 0:
                                        for i, test_code in enumerate(relevant_tests, 1):
                                            st.markdown(f"**Test {i}:**")
                                            # test_code is already formatted as markdown code block
                                            st.markdown(test_code)
                                    else:
                                        st.write("[No relevant tests provided]")
                                    st.markdown("---")
                            st.info(f"Total files reviewed: {total_files_reviewed}, total chunks reviewed: {total_chunks_reviewed}")

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
