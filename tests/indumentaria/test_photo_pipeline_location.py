from indumentaria.photo import pipeline


def test_pipeline_importable_from_new_location():
    prompts, boxes = pipeline.build_prompts(100, 200, [], None)
    assert prompts == [{"x": 50, "y": 100, "label": 1}]
    assert boxes == []
    assert hasattr(pipeline, "PipelineError")
