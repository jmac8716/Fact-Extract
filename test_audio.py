import asyncio
import edge_tts

# Text to test the voice
test_text = "System check complete. This is the new neural voice engine active on your Z13 tablet. The audio broadcast pipeline is fully functional and ready for tactical intelligence processing."

async def run_test():
    # Save it cleanly right in the current folder
    audio_filepath = "voice_test.mp3"
    
    print("🎙️ Compiling neural audio clip...")
    communicate = edge_tts.Communicate(test_text, "en-US-EmmaNeural")
    await communicate.save(audio_filepath)
    print(f"✅ Success! File saved directly in this folder as: voice_test.mp3")

if __name__ == "__main__":
    asyncio.run(run_test())