import soundfile as sf

def test_opus_conversion(opus_file):
    """
    Test Opus to WAV conversion using soundfile
    """
    # Read Opus file
    data, samplerate = sf.read(opus_file)
    
    # Write to WAV 
    wav_path = opus_file.replace('.opus', '.wav')
    sf.write(wav_path, data, samplerate, subtype="PCM_16")
    
    print(f"Converted {opus_file} to {wav_path}")
    print(f"Sample rate: {samplerate} Hz")
    print(f"Audio data shape: {data.shape}")

if __name__ == "__main__":
    # Replace with your actual .opus file path
    test_opus_conversion("input_data/sample.opus")