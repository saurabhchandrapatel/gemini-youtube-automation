"""
Enhanced Main Entry Point for AI Video Generator
Simplified, focused on the pipeline approach
"""
import os
import json
from pathlib import Path
from src.video_generator import AIVideoGenerator
from src.generator import generate_curriculum
from dotenv import load_dotenv
from src.uploader import upload_to_youtube
from src.generator import YOUR_NAME, generate_visuals
from google import genai
from google.genai import types

load_dotenv()

CONTENT_PLAN_FILE = Path("content_plan.json")
OUTPUT_DIR = Path("output")

def ensure_content_plan():
    """Ensure content plan exists"""
    if not CONTENT_PLAN_FILE.exists():
        print("📄 Generating new content plan...")
        new_plan = generate_curriculum()
        with open(CONTENT_PLAN_FILE, 'w') as f:
            json.dump(new_plan, f, indent=2)
        print(f"✅ Content plan saved to {CONTENT_PLAN_FILE}")
        return new_plan
    
    with open(CONTENT_PLAN_FILE, 'r') as f:
        return json.load(f)

def main():
    """Main execution function"""
    print("🚀 AI Video Generator - Enhanced Pipeline")
    print(f"📁 Output directory: {OUTPUT_DIR.resolve()}")
    
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Ensure content plan exists
    plan = ensure_content_plan()
    
    # Initialize video generator
    generator = AIVideoGenerator(CONTENT_PLAN_FILE, OUTPUT_DIR)
    
    # Generate summary
    summary = generator.get_generation_summary()
    print(f"\n📊 Content Summary:")
    print(f"   Total lessons: {summary['total_lessons']}")
    print(f"   Completed: {summary.get('completed', 0)}")
    print(f"   Pending: {summary.get('pending', 0)}")
    print(f"   Failed: {summary.get('failed', 0)}")
    
    if summary.get('pending', 0) == 0:
        print("\n🎉 All lessons completed! Generating new content...")
        # Generate new curriculum
        previous_titles = [lesson['title'] for lesson in plan.get('lessons', [])]
        new_plan = generate_curriculum(previous_titles=previous_titles)
        with open(CONTENT_PLAN_FILE, 'w') as f:
            json.dump(new_plan, f, indent=2)
        print("✅ New curriculum generated")
    
    # Generate next video
    print("\n🎬 Generating next video...")
    try:
        # Get next lesson
        lesson = generator.get_next_lesson()
        if not lesson:
            print("❌ No pending lessons found")
            return
            
        # Generate video using enhanced pipeline
        from src.pipeline_enhanced import run_enhanced_pipeline
        pipeline_results = run_enhanced_pipeline(lesson, OUTPUT_DIR)
        
        if pipeline_results and pipeline_results.get('final_video_path'):
            video_path = pipeline_results['final_video_path']
            print(f"✅ Video generated successfully!")
            print(f"📹 Video location: {video_path}")
            
            # Upload to YouTube
            print("\n📤 Uploading to YouTube...")
            youtube_id = upload_video_to_youtube(lesson, video_path, pipeline_results)
            
            if youtube_id:
                # Update lesson status
                generator.update_lesson_status(lesson['title'], 'completed', video_path)
                print(f"✅ Uploaded to YouTube: {youtube_id}")
            else:
                print("❌ YouTube upload failed")
                
            # Show updated summary
            updated_summary = generator.get_generation_summary()
            print(f"\n📊 Updated Summary:")
            print(f"   Completed: {updated_summary.get('completed', 0)}")
            print(f"   Pending: {updated_summary.get('pending', 0)}")
        else:
            print("❌ Video generation failed")
            
    except Exception as e:
        print(f"❌ Error in video generation: {e}")
        import traceback
        traceback.print_exc()

def generate_ai_thumbnail(output_dir, thumbnail_text, lesson_title):
    """Generate AI thumbnail using Gemini"""
    try:
        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
        
        prompt = f"""
        Create a professional YouTube thumbnail for: "{lesson_title}"
        
        Text overlay: "{thumbnail_text}"
        
        Style: Eye-catching, professional, educational, high contrast
        Colors: Bright, engaging colors that stand out
        Layout: Clean, readable text with compelling visuals
        Aspect ratio: 16:9 (1280x720)
        
        Requirements:
        - Bold, readable text
        - Professional educational design
        - High click-through rate potential
        - YouTube thumbnail best practices
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE'],
                image_config=types.ImageConfig(
                    aspect_ratio="16:9",
                    image_size="LARGE"
                ),
            )
        )
        
        for part in response.parts:
            if image := part.as_image():
                thumbnail_path = output_dir / "ai_thumbnail.png"
                image.save(thumbnail_path)
                print(f"🖼️ Generated AI thumbnail: {thumbnail_path}")
                return str(thumbnail_path)
        
        # Fallback to text-based thumbnail
        return generate_visuals(
            output_dir=output_dir,
            video_type='long',
            thumbnail_title=thumbnail_text
        )
        
    except Exception as e:
        print(f"❌ AI thumbnail generation failed: {e}")
        # Fallback to text-based thumbnail
        return generate_visuals(
            output_dir=output_dir,
            video_type='long',
            thumbnail_title=thumbnail_text
        )

def upload_video_to_youtube(lesson, video_path, pipeline_results):
    """Upload generated video to YouTube with AI-generated metadata"""
    try:
        output_dir = Path(pipeline_results['output_directory'])
        
        # Get AI-generated metadata
        youtube_metadata = pipeline_results.get('youtube_metadata', {})
        
        # Use pipeline-generated thumbnail
        thumbnail_path = pipeline_results.get('thumbnail_path')
        if not thumbnail_path:
            # Fallback to generating thumbnail
            thumbnail_text = youtube_metadata.get('thumbnail_text', lesson['title'])
            thumbnail_path = generate_ai_thumbnail(output_dir, thumbnail_text, lesson['title'])
        
        # Use AI-generated metadata
        title = youtube_metadata.get('optimized_title', lesson['title'])
        description = youtube_metadata.get('description', f"Educational video about {lesson['title']}")
        hashtags = youtube_metadata.get('hashtags', '#AI #Education #Learning')
        tags = ', '.join(youtube_metadata.get('tags', ['AI', 'Education', 'Tutorial']))
        
        # Enhance description
        full_description = f"{description}\n\nPart of the 'AI for Developers' series by {YOUR_NAME}.\n\n{hashtags}"
        
        # Upload to YouTube
        youtube_id = upload_to_youtube(
            video_path,
            title,
            full_description,
            tags,
            thumbnail_path
        )
        
        print(f"🏷️ Using AI metadata: {title[:50]}...")
        return youtube_id
        
    except Exception as e:
        print(f"❌ YouTube upload error: {e}")
        return None

def batch_mode(count=3):
    """Generate multiple videos in batch mode"""
    print(f"🚀 Batch Mode: Generating {count} videos")
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    ensure_content_plan()
    
    try:
        generator = AIVideoGenerator(CONTENT_PLAN_FILE, OUTPUT_DIR)
        results = generator.generate_batch_videos(count)
        
        print(f"\n✅ Batch generation completed!")
        print(f"📊 Generated {len(results)} videos:")
        
        for result in results:
            print(f"   📹 {result['lesson']}")
            print(f"      Path: {result['video_path']}")
        
        return results
        
    except Exception as e:
        print(f"❌ Batch generation failed: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        batch_mode(count)
    else:
        main()