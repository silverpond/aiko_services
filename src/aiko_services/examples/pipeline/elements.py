# Usage
# ~~~~~
# cd ../examples/pipeline
# aiko_pipeline create pipeline_local.json
# aiko_pipeline create pipeline_remote.json
# aiko_pipeline create pipeline_test.json
#
# TOPIC=$NAMESPACE/$HOST/$PID/$SID/in
# mosquitto_pub -h $HOST -t $TOPIC -m "(create_stream 1)"
# mosquitto_pub -h $HOST -t $TOPIC -m "(process_frame (stream_id: 1) (a: 0))"
# mosquitto_pub -h $HOST -t $TOPIC -m "(destroy_stream 1)"
#
# To Do
# ~~~~~
# - PE_Metrics: Make visible to Aiko Dashboard via self.share[]
# - PE_Metrics: Store to file (JSON, CSV), SQLite, InfluxDB
# - PE_Metrics: Add run-time average calculation
#
# - Consider PE_DataDecode and PE_DataEncode using "kwargs" for flexible
#   choices of data type to transfer via function parameters

import base64
from io import BytesIO
import numpy as np
from typing import Tuple

import aiko_services as aiko

# --------------------------------------------------------------------------- #

import time

class PE_Add(aiko.PipelineElement):
    def __init__(self, context):
        context.set_protocol("add:0")
        context.get_implementation("PipelineElement").__init__(self, context)

    def process_frame(self, stream, i) -> Tuple[aiko.StreamEvent, dict]:
        constant, _ = self.get_parameter("constant", default=1)
        i_new = int(i) + int(constant)

        self.logger.info(f"{self._id(stream)}, i in: {i}, out: {i_new}")

        delay, _ = self.get_parameter("delay", default=0)  # seconds
        if delay:
            time.sleep(float(delay))

        return aiko.StreamEvent.OKAY, {"i": i_new}

# --------------------------------------------------------------------------- #
# PE_Metrics typically appears at the end of a Pipeline graph.
# So that child Pipeline responses can be returned to the parent Pipeline,
# the PE_Metrics PipelineElement Definition can refer to any output
# produced by the prior PipelineElements in the Pipeline graph
#
# For example ... "output": [{ "name": "i", "type": "int" }]

class PE_Metrics(aiko.PipelineElement):
    def __init__(self, context):
        context.set_protocol("metrics:0")
        context.get_implementation("PipelineElement").__init__(self, context)

    def process_frame(self, stream) -> Tuple[aiko.StreamEvent, dict]:
        metrics = stream["metrics"]
        metrics_elements = metrics["pipeline_elements"]
        for metrics_name, metrics_value in metrics_elements.items():
            metrics_value *= 1000
            self.logger.debug(f"{metrics_name}: {metrics_value:.3f} ms")

        time_pipeline = metrics["time_pipeline"] * 1000
        self.logger.debug(f"Pipeline total: {time_pipeline:.3f} ms")

        outputs = {}
        for output_definition in self.definition.output:
            output_name = output_definition["name"]
            outputs[output_name] = stream["swag"][output_name]

        return aiko.StreamEvent.OKAY, outputs

# --------------------------------------------------------------------------- #

import random

class PE_RandomIntegers(aiko.PipelineElement):
    def __init__(self, context: aiko.ContextPipelineElement):
        context.set_protocol("random_integers:0")  # data_source:0
        context.get_implementation("PipelineElement").__init__(self, context)

    def frame_generator(self, stream):
        limit, _ = self.get_parameter("limit")
        if stream["frame_id"] < int(limit):
            return aiko.StreamEvent.OKAY, {"random": random.randint(0, 9)}
        else:
            return aiko.StreamEvent.STOP, None

    def start_stream(self, stream, stream_id):
        rate, _ = self.get_parameter("rate", default=1)
        self.create_frames(stream, self.frame_generator, rate=float(rate))
        return aiko.StreamEvent.OKAY, None

    def process_frame(self, stream, random) -> Tuple[aiko.StreamEvent, dict]:
    #   if stream["stream_id"] == 0:  # TODO: "stream_required"
    #       return aiko.StreamEvent.ERROR, "Must create a stream"

        self.logger.info(f"{self._id(stream)}: random: {random}")
        return aiko.StreamEvent.OKAY, {"random": random}

    def stop_stream(self, stream, stream_id):
        stream["terminate"] = True

# --------------------------------------------------------------------------- #

class PE_0(aiko.PipelineElement):
    def __init__(self, context):
        context.set_protocol("increment:0")
        context.get_implementation("PipelineElement").__init__(self, context)

    def process_frame(self, stream, a) -> Tuple[aiko.StreamEvent, dict]:
        pe_0_inc, found = self.get_parameter("pe_0_inc", 1)
        b = int(a) + int(pe_0_inc)
        self.logger.info(f"PE_0: {self._id(stream)}, in a: {a}, out b: {b}")
        return aiko.StreamEvent.OKAY, {"b": b}

# --------------------------------------------------------------------------- #

class PE_1(aiko.PipelineElement):
    def __init__(self, context):
        context.set_protocol("increment:0")
        context.get_implementation("PipelineElement").__init__(self, context)

    def process_frame(self, stream, b) -> Tuple[aiko.StreamEvent, dict]:
        increment = 1
        p_1, found = self.get_parameter("p_1")
        pe_1_inc, found = self.get_parameter("pe_1_inc", 1)
        c = int(b) + int(pe_1_inc)
        self.logger.info(f"PE_1: {self._id(stream)}, in b: {b}, out c: {c}")
        self.logger.info(f"PE_1:            parameter pe_1_inc: {pe_1_inc}")
        return aiko.StreamEvent.OKAY, {"c": c}

# --------------------------------------------------------------------------- #

class PE_2(aiko.PipelineElement):
    def __init__(self, context):
        context.set_protocol("increment:0")
        context.get_implementation("PipelineElement").__init__(self, context)

    def process_frame(self, stream, c) -> Tuple[aiko.StreamEvent, dict]:
        d = int(c) + 1
        self.logger.info(f"PE_2: {self._id(stream)}, in c: {c}, out d: {d}")
        return aiko.StreamEvent.OKAY, {"d": d}

# --------------------------------------------------------------------------- #

class PE_3(aiko.PipelineElement):
    def __init__(self, context):
        context.set_protocol("increment:0")
        context.get_implementation("PipelineElement").__init__(self, context)

    def process_frame(self, stream, c) -> Tuple[aiko.StreamEvent, dict]:
        e = int(c) + 1
        self.logger.info(f"PE_3: {self._id(stream)}, in c: {c}, out e: {e}")
        return aiko.StreamEvent.OKAY, {"e": e}

# --------------------------------------------------------------------------- #

class PE_4(aiko.PipelineElement):
    def __init__(self, context):
        context.set_protocol("sum:0")
        context.get_implementation("PipelineElement").__init__(self, context)

    def process_frame(self, stream, d, e) -> Tuple[aiko.StreamEvent, dict]:
        f = int(d) + int(e)
        self.logger.info(
            f"PE_4: {self._id(stream)}, in d, e {d} {e}, out: d + e = f: {f}")
        return aiko.StreamEvent.OKAY, {"f": f}

# --------------------------------------------------------------------------- #

class PE_DataDecode(aiko.PipelineElement):
    def __init__(self, context):
        context.get_implementation("PipelineElement").__init__(self, context)

    def process_frame(self, stream, data) -> Tuple[aiko.StreamEvent, dict]:
        data = base64.b64decode(data.encode("utf-8"))
        np_bytes = BytesIO(data)
        data = np.load(np_bytes, allow_pickle=True)
    #   self.logger.info(f"{self._id(stream)}, data: {data}")
        return aiko.StreamEvent.OKAY, {"data": data}

# --------------------------------------------------------------------------- #

class PE_DataEncode(aiko.PipelineElement):
    def __init__(self, context):
        context.get_implementation("PipelineElement").__init__(self, context)

    def process_frame(self, stream, data) -> Tuple[aiko.StreamEvent, dict]:
    #   self.logger.info(f"{self._id(stream)}, data: {data}")
        if isinstance(data, str):
            data = str.encode(data)
        if isinstance(data, np.ndarray):
            np_bytes = BytesIO()
            np.save(np_bytes, data, allow_pickle=True)
            data = np_bytes.getvalue()
        data = base64.b64encode(data).decode("utf-8")
        return aiko.StreamEvent.OKAY, {"data": data}

# --------------------------------------------------------------------------- #
