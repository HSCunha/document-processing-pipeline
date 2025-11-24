from extract_metadata.core.cleaning import (
    CleaningPipeline,
    ExcessBreakLineRemover,
    PatternRemover,
    SelectionTagReplacer,
    MarkdownConverter
)

def get_generic_cleaning_pipeline() -> CleaningPipeline:
    """
    Returns a generic cleaning pipeline with common cleaning steps.
    """
    return CleaningPipeline(cleaners=[
        ExcessBreakLineRemover(),
        PatternRemover(),
        SelectionTagReplacer(),
        MarkdownConverter()
    ])
