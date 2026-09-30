import logging
import threading
from types import SimpleNamespace

import aiko_services as aiko
from aiko_services.main.pipeline import PipelineElementImpl
from aiko_services.main.stream import Stream, StreamState


class _Pipeline:
    name = "test"
    DEBUG = {}

    def _enable_thread_local(self, *_args):
        pass

    def _disable_thread_local(self, *_args):
        pass

    def _process_stream_event(self, _name, _stream, _event, _frame_data):
        return StreamState.STOP


def test_frame_generator_does_not_hold_stream_lock():
    stream = Stream(stream_id="0")
    pipeline = _Pipeline()
    pipeline.stream_leases = {"0": SimpleNamespace(stream=stream)}
    element = SimpleNamespace(
        pipeline=pipeline,
        logger=logging.getLogger(__name__),
        name="Test",
        get_stream=lambda: (stream, 0),
    )

    lock_available = threading.Event()
    lock_was_available = []

    def frame_generator(current_stream, _frame_id):
        acquired = current_stream.lock._lock.acquire(timeout=0.2)
        lock_was_available.append(acquired)
        if acquired:
            current_stream.lock._lock.release()
        lock_available.set()
        return aiko.StreamEvent.STOP, {}

    worker = threading.Thread(
        target=PipelineElementImpl._create_frames_generator,
        args=(element, stream, frame_generator, 0, 1),
    )
    worker.start()
    worker.join(timeout=1)

    assert not worker.is_alive()
    assert lock_available.is_set()
    assert lock_was_available == [True]


def test_frame_generator_drops_replaced_stream_result():
    stream = Stream(stream_id="0")
    replacement = Stream(stream_id="0")
    pipeline = _Pipeline()
    pipeline.stream_leases = {"0": SimpleNamespace(stream=replacement)}
    processed = []
    pipeline._process_stream_event = lambda *_args: processed.append(True)
    element = SimpleNamespace(
        pipeline=pipeline,
        logger=logging.getLogger(__name__),
        name="Test",
        get_stream=lambda: (stream, 0),
    )

    worker = threading.Thread(
        target=PipelineElementImpl._create_frames_generator,
        args=(element, stream, lambda *_args: (aiko.StreamEvent.OKAY, {"value": 1}), 0, 1),
    )
    worker.start()
    worker.join(timeout=1)

    assert not worker.is_alive()
    assert processed == []


def test_frame_generator_does_not_overwrite_stop_result():
    stream = Stream(stream_id="0")
    pipeline = _Pipeline()
    pipeline.stream_leases = {"0": SimpleNamespace(stream=stream)}
    processed = []
    pipeline._process_stream_event = lambda *_args: processed.append(True)
    element = SimpleNamespace(
        pipeline=pipeline,
        logger=logging.getLogger(__name__),
        name="Test",
        get_stream=lambda: (stream, 0),
    )

    def frame_generator(current_stream, _frame_id):
        current_stream.state = StreamState.STOP
        return aiko.StreamEvent.OKAY, {"value": 1}

    worker = threading.Thread(
        target=PipelineElementImpl._create_frames_generator,
        args=(element, stream, frame_generator, 0, 1),
    )
    worker.start()
    worker.join(timeout=1)

    assert not worker.is_alive()
    assert processed == []
    assert stream.state == StreamState.STOP
