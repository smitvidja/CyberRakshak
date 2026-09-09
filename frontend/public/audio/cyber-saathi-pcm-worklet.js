class CyberSaathiPcmProcessor extends AudioWorkletProcessor {
  process(inputs, outputs) {
    const input = inputs[0]?.[0];
    if (input?.length) this.port.postMessage(new Float32Array(input));
    const output = outputs[0]?.[0];
    if (output) output.fill(0);
    return true;
  }
}

registerProcessor("cyber-saathi-pcm", CyberSaathiPcmProcessor);
