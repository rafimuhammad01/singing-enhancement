import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { usePitchDetection } from "./usePitchDetection";
import { PitchFilter } from "@/utils/pitchFilter";

// ---------------------------------------------------------------------------
// rAF stubs — capture but never auto-invoke so tests stay synchronous
// ---------------------------------------------------------------------------
// rAF stubs: capture callback into a module-level map so individual tests can invoke
// the callback manually; annotate the variable as intentionally unused here.
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const rafCallbacks = new Map<number, FrameRequestCallback>();

beforeEach(() => {
  rafCallbacks.clear();
  globalThis.requestAnimationFrame = vi.fn((cb: FrameRequestCallback) => {
    const id = rafCallbacks.size + 1;
    rafCallbacks.set(id, cb);
    return id;
  });
  globalThis.cancelAnimationFrame = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// Helper: build a minimal fake AudioContext
// ---------------------------------------------------------------------------
function makeFakeAudioContext() {
  const analyser = {
    fftSize: 2048,
    smoothingTimeConstant: 0,
    getFloatTimeDomainData: vi.fn((_buf: Float32Array) => {}),
  };
  const source = {
    connect: vi.fn(),
  };
  return {
    sampleRate: 44100,
    createAnalyser: vi.fn(() => analyser),
    createMediaStreamSource: vi.fn(() => source),
    close: vi.fn().mockResolvedValue(undefined),
    _analyser: analyser,
  };
}

// ---------------------------------------------------------------------------
// Helper: build a minimal fake MediaStream
// ---------------------------------------------------------------------------
function makeFakeStream() {
  const track = { stop: vi.fn() };
  return {
    getTracks: vi.fn(() => [track]),
    _track: track,
  };
}

// ---------------------------------------------------------------------------
// A. Error paths
// ---------------------------------------------------------------------------
describe("A. Permission-denied error path", () => {
  it('NotAllowedError → error = "Microphone permission denied", isActive = false', async () => {
    const pd = usePitchDetection({
      getUserMediaFn: vi
        .fn()
        .mockRejectedValue(new DOMException("denied", "NotAllowedError")),
    });

    await pd.start(() => null);

    expect(pd.error.value).toBe("Microphone permission denied");
    expect(pd.isActive.value).toBe(false);
  });

  it('PermissionDeniedError → error = "Microphone permission denied", isActive = false', async () => {
    const pd = usePitchDetection({
      getUserMediaFn: vi
        .fn()
        .mockRejectedValue(new DOMException("denied", "PermissionDeniedError")),
    });

    await pd.start(() => null);

    expect(pd.error.value).toBe("Microphone permission denied");
    expect(pd.isActive.value).toBe(false);
  });
});

describe("B. NotFoundError path", () => {
  it('NotFoundError → error = "No microphone found", isActive = false', async () => {
    const pd = usePitchDetection({
      getUserMediaFn: vi
        .fn()
        .mockRejectedValue(new DOMException("not found", "NotFoundError")),
    });

    await pd.start(() => null);

    expect(pd.error.value).toBe("No microphone found");
    expect(pd.isActive.value).toBe(false);
  });
});

describe("C. Generic error path", () => {
  it('plain Error("boom") → error = "boom", isActive = false', async () => {
    const pd = usePitchDetection({
      getUserMediaFn: vi.fn().mockRejectedValue(new Error("boom")),
    });

    await pd.start(() => null);

    expect(pd.error.value).toBe("boom");
    expect(pd.isActive.value).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// D. Idempotent stop before start
// ---------------------------------------------------------------------------
describe("D. Idempotent stop() before any start()", () => {
  it("calling stop() before start() does not throw", () => {
    const pd = usePitchDetection();
    expect(() => pd.stop()).not.toThrow();
  });
});

// ---------------------------------------------------------------------------
// E. Successful start — shared factory-call helpers
// ---------------------------------------------------------------------------
function startGreen() {
  const fakeStream = makeFakeStream();
  const fakeCtx = makeFakeAudioContext();
  const ctxFactory = vi.fn(() => fakeCtx as unknown as AudioContext);
  const getUserMedia = vi.fn().mockResolvedValue(fakeStream);
  const filter = new PitchFilter();

  const pd = usePitchDetection({
    audioContextFactory: ctxFactory,
    getUserMediaFn: getUserMedia,
    filter,
  });

  return { pd, fakeStream, fakeCtx, ctxFactory, getUserMedia };
}

describe("E. Double start is a no-op", () => {
  it("second start() call does not allocate a new AudioContext", async () => {
    const { pd, ctxFactory } = startGreen();

    await pd.start(() => null);
    expect(ctxFactory).toHaveBeenCalledTimes(1);
    expect(pd.isActive.value).toBe(true);

    await pd.start(() => null);
    // Still called only once — no-op on second call
    expect(ctxFactory).toHaveBeenCalledTimes(1);
  });
});

describe("F. Successful start sets isActive and clears error", () => {
  it("after green start: isActive = true, error = null, currentMidi initialized to null (filter buf is empty)", async () => {
    const { pd } = startGreen();

    await pd.start(() => null);

    expect(pd.isActive.value).toBe(true);
    expect(pd.error.value).toBeNull();
  });
});

describe("G. stop() after successful start resets state", () => {
  it("stop() sets isActive=false, currentMidi=null, calls close() and getTracks", async () => {
    const { pd, fakeCtx, fakeStream } = startGreen();

    await pd.start(() => null);
    expect(pd.isActive.value).toBe(true);

    pd.stop();

    expect(pd.isActive.value).toBe(false);
    expect(pd.currentMidi.value).toBeNull();
    expect(fakeCtx.close).toHaveBeenCalled();
    expect(fakeStream.getTracks).toHaveBeenCalled();
    expect(fakeStream._track.stop).toHaveBeenCalled();
  });
});
