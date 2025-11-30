import json
import os
import time
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

class VideoProductionPipeline:
    def __init__(self, lesson_data, output_base_dir="output"):
        self.lesson = lesson_data
        self.unique_id = f"{datetime.now().strftime('%Y%m%d')}_{lesson_data['chapter']}_{lesson_data['part']}"
        self.output_dir = Path(output_base_dir) / f"lesson_{self.unique_id}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Pipeline state to pass data between steps
        self.pipeline_state = {
            "lesson_data": lesson_data,
            "concept": None,
            "research": None,
            "script": None,
            "storyboard": None,
            "assets": {},
            "final_video_path": None
        }
    
    def save_step_output(self, step_name, data):
        """Save step output to file and pipeline state"""
        file_path = self.output_dir / f"{step_name.lower().replace(' ', '_')}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return data
    
    def step_1_concept_development(self):
        """Generate core concept and angles"""
        prompt = f"""
        Act as a Creative Director. Generate a comprehensive concept for: "{self.lesson['title']}"
        
        Return JSON with:
        {{
            "main_concept": "Core idea in 1-2 sentences",
            "target_audience": "Specific audience description",
            "purpose": "educate/inspire/entertain",
            "unique_angles": ["angle1", "angle2", "angle3"],
            "key_takeaways": ["takeaway1", "takeaway2", "takeaway3"],
            "hook_ideas": ["hook1", "hook2", "hook3"]
        }}
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        concept_data = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
        
        self.pipeline_state["concept"] = concept_data
        return self.save_step_output("concept", concept_data)
    
    def step_2_research_validation(self):
        """Research and validate concept"""
        concept = self.pipeline_state["concept"]
        
        prompt = f"""
        Act as a Research Strategist. Based on this concept: {concept["main_concept"]}
        
        Return JSON with:
        {{
            "market_analysis": "Current trends and gaps",
            "competitor_insights": "What others are doing",
            "content_gaps": ["gap1", "gap2"],
            "unique_positioning": "How to stand out",
            "key_points_to_cover": ["point1", "point2", "point3"],
            "trending_keywords": ["keyword1", "keyword2", "keyword3"]
        }}
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        research_data = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
        
        self.pipeline_state["research"] = research_data
        return self.save_step_output("research", research_data)
    
    def step_3_script_writing(self):
        """Generate complete script with multiple 7-second segments"""
        concept = self.pipeline_state["concept"]
        research = self.pipeline_state["research"]
        
        prompt = f"""
        Act as a Scriptwriter. Create a script for: "{self.lesson['title']}"
        
        Concept: {concept["main_concept"]}
        Key Points: {research["key_points_to_cover"]}
        
        Create multiple 7-second video segments that will be merged together.
        
        Return JSON with:
        {{
            "segments": [
                {{"segment_id": 1, "script": "7-second narration (max 15-20 words)", "visual_cue": "Visual description"}},
                {{"segment_id": 2, "script": "7-second narration (max 15-20 words)", "visual_cue": "Visual description"}}
            ],
            "total_segments": 3,
            "total_duration_estimate": 21
        }}
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        script_data = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
        
        self.pipeline_state["script"] = script_data
        return self.save_step_output("script", script_data)
    
    def step_4_storyboard_planning(self):
        """Create storyboard for multiple 7-second segments"""
        script = self.pipeline_state["script"]
        
        prompt = f"""
        Act as a Director. Create storyboard for multiple 7-second video segments about {self.lesson['title']}.
        
        Segments: {script["segments"]}
        
        Return JSON with:
        {{
            "segments": [
                {{
                    "segment_id": 1,
                    "visual_description": "Compelling visual for AI video generation",
                    "duration": 7
                }}
            ],
            "visual_style": "Dynamic, engaging, educational",
            "aspect_ratio": "16:9"
        }}
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        storyboard_data = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
        
        self.pipeline_state["storyboard"] = storyboard_data
        return self.save_step_output("storyboard", storyboard_data)
    
    def generate_ai_video_segment(self, prompt, visual_description, output_path):
        """Generate 7-second video using Veo with image input"""
        try:
            # Step 1: Generate image first
            image_response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=visual_description,
                config={"response_modalities": ["IMAGE"]}
            )
            
            image = image_response.parts[0].as_image()
            print(f"🖼️ Generated base image for video")
            
            # Step 2: Generate video with Veo using the image
            operation = client.models.generate_videos(
                model="veo-3.1-generate-preview",
                prompt=prompt,
                image=image,
            )
            
            # Poll until video is ready
            while not operation.done:
                print("⏳ Waiting for video generation...")
                time.sleep(10)
                operation = client.operations.get(operation)
            
            # Download the video
            video = operation.response.generated_videos[0]
            client.files.download(file=video.video)
            video.video.save(output_path)
            
            print(f"🎬 Generated 7-sec video: {output_path}")
            return str(output_path)
            
        except Exception as e:
            print(f"❌ AI video generation failed: {e}")
            return None
    
    def step_5_asset_generation(self):
        """Generate video segments using AI"""
        script = self.pipeline_state["script"]
        storyboard = self.pipeline_state["storyboard"]
        
        assets = {
            "video_segments": [],
            "metadata": {}
        }
        
        # Generate AI video segments
        for i, segment in enumerate(script["segments"]):
            segment_path = self.output_dir / f"segment_{i+1}_{self.unique_id}.mp4"
            
            video_prompt = f"Educational video about {self.lesson['title']}: {segment['script']}"
            visual_description = f"Professional educational image: {segment['visual_cue']}, 16:9 aspect ratio, clean modern style"
            
            ai_video_path = self.generate_ai_video_segment(video_prompt, visual_description, segment_path)
            if ai_video_path:
                assets["video_segments"].append(ai_video_path)
        
        assets["metadata"] = {
            "total_segments": len(script["segments"]),
            "generated_segments": len(assets["video_segments"])
        }
        
        self.pipeline_state["assets"] = assets
        return self.save_step_output("assets", assets)
    
    def step_6_youtube_metadata_generation(self):
        """Generate YouTube metadata using AI"""
        concept = self.pipeline_state["concept"]
        script = self.pipeline_state["script"]
        storyboard = self.pipeline_state["storyboard"]
        
        prompt = f"""
        Act as a YouTube SEO Expert. Generate optimized metadata for: "{self.lesson['title']}"
        
        Content Context:
        - Concept: {concept["main_concept"]}
        - Script segments: {[seg['script'] for seg in script['segments']]}
        - Visual style: {storyboard.get('visual_style', 'Educational')}
        
        Return JSON with:
        {{
            "optimized_title": "SEO-optimized title (max 60 chars)",
            "description": "Engaging description with keywords",
            "hashtags": "#hashtag1 #hashtag2 #hashtag3",
            "tags": ["tag1", "tag2", "tag3"],
            "thumbnail_text": "Eye-catching thumbnail text"
        }}
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        metadata = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
        
        self.pipeline_state["youtube_metadata"] = metadata
        return self.save_step_output("youtube_metadata", metadata)
    
    def step_7_thumbnail_generation(self):
        """Generate AI thumbnail"""
        youtube_metadata = self.pipeline_state["youtube_metadata"]
        thumbnail_text = youtube_metadata.get('thumbnail_text', self.lesson['title'])
        
        try:
            prompt = f"""
            Create a professional YouTube thumbnail for: "{self.lesson['title']}"
            
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
                    thumbnail_path = self.output_dir / "ai_thumbnail.png"
                    image.save(thumbnail_path)
                    print(f"🖼️ Generated AI thumbnail: {thumbnail_path}")
                    
                    self.pipeline_state["thumbnail_path"] = str(thumbnail_path)
                    return self.save_step_output("thumbnail", {"path": str(thumbnail_path), "text": thumbnail_text})
            
            print("❌ No thumbnail generated")
            return None
            
        except Exception as e:
            print(f"❌ AI thumbnail generation failed: {e}")
            return None
    
    def step_8_video_creation(self):
        """Merge 7-second videos with MoviePy"""
        assets = self.pipeline_state["assets"]
        
        if assets["video_segments"]:
            from moviepy.editor import VideoFileClip, concatenate_videoclips
            
            clips = [VideoFileClip(path) for path in assets["video_segments"]]
            final_video = concatenate_videoclips(clips)
            
            final_path = self.output_dir / f"final_video_{self.unique_id}.mp4"
            final_video.write_videofile(str(final_path), fps=24)
            
            # Cleanup
            for clip in clips:
                clip.close()
            final_video.close()
            
            self.pipeline_state["final_video_path"] = str(final_path)
        else:
            print("❌ No video segments generated")
            return None
        
        summary = {
            "lesson_title": self.lesson["title"],
            "video_path": self.pipeline_state["final_video_path"],
            "output_directory": str(self.output_dir),
            "segments_generated": len(assets["video_segments"]),
            "youtube_metadata": self.pipeline_state.get("youtube_metadata", {}),
            "pipeline_completed": True,
            "timestamp": datetime.now().isoformat()
        }
        
        return self.save_step_output("final_summary", summary)
    
    def run_complete_pipeline(self):
        """Execute the complete pipeline"""
        print(f"🚀 Starting complete pipeline for: {self.lesson['title']}")
        print(f"📁 Output directory: {self.output_dir}")
        
        try:
            print("Step 1: Concept Development")
            self.step_1_concept_development()
            
            print("Step 2: Research & Validation")
            self.step_2_research_validation()
            
            print("Step 3: Script Writing")
            self.step_3_script_writing()
            
            print("Step 4: Storyboard Planning")
            self.step_4_storyboard_planning()
            
            print("Step 5: Asset Generation")
            self.step_5_asset_generation()
            
            print("Step 6: YouTube Metadata Generation")
            self.step_6_youtube_metadata_generation()
            
            print("Step 7: Thumbnail Generation")
            self.step_7_thumbnail_generation()
            
            print("Step 8: Video Creation")
            self.step_8_video_creation()
            
            print(f"✅ Pipeline completed successfully!")
            print(f"📁 All outputs saved to: {self.output_dir}")
            
            return self.pipeline_state
            
        except Exception as e:
            print(f"❌ Pipeline failed: {e}")
            raise

def run_enhanced_pipeline(lesson_data, output_dir="output"):
    """Main function to run the enhanced pipeline"""
    pipeline = VideoProductionPipeline(lesson_data, output_dir)
    return pipeline.run_complete_pipeline()