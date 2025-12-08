import aiko_services as aiko
from aiko_services.main.pipeline import (
    _PIPELINE_HOOK_DESTROY_STREAM,
)
from aiko_services.main.stream import StreamEvent, StreamState
from aiko_services.tests.unit import do_create_pipeline

PIPELINE_DEFINITION = """{
  "version": 0, "name": "p_test", "runtime": "python",
  "graph": ["(A)"],
  "elements": [
    { "name":   "A",
      "input":  [{ "name": "a", "type": "int" }],
      "output": [{ "name": "a", "type": "int" }],
      "deploy": {
        "local": { "module": "aiko_services.tests.unit.test_pipeline_exception_handling" }
      }
    }
  ]
}
"""

class A(aiko.PipelineElement):
    def __init__(self, context):
        context.call_init(self, "PipelineElement", context)

    def frame_generator(self, stream, frame_id):
        if frame_id == 0:
            return StreamEvent.OKAY, {"a": 1}
        else:
            return StreamEvent.STOP, {}

    def process_frame(self):
        return StreamEvent.OKAY, {}

    def start_stream(self, stream, stream_id):
        raise Exception("TEST")
        return StreamEvent.OKAY, None

    def stop_stream(self, stream, stream_id):
        self.stop()
        return StreamEvent.OKAY, None


def test_pipeline_hooks():
    def hook_destroy_stream(hook_name, component, logger, variables, options):
        assert variables["stream"].state == StreamState.ERROR

    hooks = {
        _PIPELINE_HOOK_DESTROY_STREAM: hook_destroy_stream,
    }
    do_create_pipeline(PIPELINE_DEFINITION, hooks=hooks)
