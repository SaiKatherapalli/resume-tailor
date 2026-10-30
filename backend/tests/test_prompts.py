from core.prompts import analyze_prompt, import_prompt, rewrite_prompt


def test_blanks_are_what_we_expect():
    # If someone renames a blank by mistake, this test catches it.
    assert set(analyze_prompt.input_variables) == {"job_description"}
    assert set(import_prompt.input_variables) == {"resume_text"}
    assert set(rewrite_prompt.input_variables) == {
        "job_title",
        "responsibilities",
        "honest_keywords",
        "missing_keywords",
        "original_summary",
        "skills_bank",
        "experiences",
        "feedback",
    }


def test_job_description_goes_inside_tags():
    messages = analyze_prompt.invoke({"job_description": "Need a Kafka expert"}).to_messages()
    assert "<job_description>\nNeed a Kafka expert\n</job_description>" in messages[1].content
