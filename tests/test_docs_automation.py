from scripts.validate_doc_counts import validate_docs


def test_generated_documentation_is_current():
    assert validate_docs() == []
