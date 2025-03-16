declare module 'recorder-js' {
  export interface RecorderOptions {
    onAnalysed?: (data: any) => void;
    bufferLength?: number;
  }
  
  export interface StopResult {
    blob: Blob;
    buffer: AudioBuffer | null;
  }
  
  export default class Recorder {
    constructor(context: AudioContext, config?: RecorderOptions);
    init(stream: MediaStream): Promise<void>;
    start(): Promise<void>;
    stop(): Promise<StopResult>;
    clear(): void;
    download(filename?: string): void;
  }
} 