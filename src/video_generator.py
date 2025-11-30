"""
Enhanced Video Generator that integrates with the pipeline
Combines AI-generated content with video production
"""
import json
from pathlib import Path
from .pipeline_enhanced import VideoProductionPipeline
from .generator import create_video, generate_visuals, text_to_speech

class AIVideoGenerator:
    def __init__(self, content_plan_path="content_plan.json", output_base="output"):
        self.content_plan_path = Path(content_plan_path)
        self.output_base = Path(output_base)
        self.output_base.mkdir(exist_ok=True)
    
    def get_next_lesson(self):
        """Get the next pending lesson from content plan"""
        if not self.content_plan_path.exists():
            return None
            
        with open(self.content_plan_path, 'r') as f:
            plan = json.load(f)
        
        for lesson in plan.get('lessons', []):
            if lesson.get('status') == 'pending':
                return lesson
        return None
    
    def update_lesson_status(self, lesson_title, status, video_path=None):
        """Update lesson status in content plan"""
        with open(self.content_plan_path, 'r') as f:
            plan = json.load(f)
        
        for lesson in plan.get('lessons', []):
            if lesson.get('title') == lesson_title:
                lesson['status'] = status
                if video_path:
                    lesson['video_path'] = str(video_path)
                break
        
        with open(self.content_plan_path, 'w') as f:
            json.dump(plan, f, indent=2)
    
    def generate_single_video(self, lesson_data=None):
        """Generate a single video using the enhanced pipeline"""
        if not lesson_data:
            lesson_data = self.get_next_lesson()
            if not lesson_data:
                print("No pending lessons found")
                return None
        
        print(f"🎬 Generating video for: {lesson_data['title']}")
        
        try:
            # Run the enhanced pipeline
            pipeline = VideoProductionPipeline(lesson_data, self.output_base)
            results = pipeline.run_complete_pipeline()
            
            # Update status
            video_path = results.get('final_video_path')
            if video_path:
                self.update_lesson_status(
                    lesson_data['title'], 
                    'completed', 
                    video_path
                )
                print(f"✅ Video generated successfully: {video_path}")
                return video_path
            else:
                print("❌ Video generation failed - no output path")
                return None
                
        except Exception as e:
            print(f"❌ Error generating video: {e}")
            self.update_lesson_status(lesson_data['title'], 'failed')
            return None
    
    def generate_batch_videos(self, count=1):
        """Generate multiple videos in batch"""
        generated_videos = []
        
        for i in range(count):
            lesson = self.get_next_lesson()
            if not lesson:
                print(f"No more pending lessons. Generated {len(generated_videos)} videos.")
                break
            
            video_path = self.generate_single_video(lesson)
            if video_path:
                generated_videos.append({
                    'lesson': lesson['title'],
                    'video_path': video_path
                })
        
        return generated_videos
    
    def get_generation_summary(self):
        """Get summary of all generated content"""
        summary = {
            'total_lessons': 0,
            'completed': 0,
            'pending': 0,
            'failed': 0,
            'output_directories': []
        }
        
        if self.content_plan_path.exists():
            with open(self.content_plan_path, 'r') as f:
                plan = json.load(f)
            
            for lesson in plan.get('lessons', []):
                summary['total_lessons'] += 1
                status = lesson.get('status', 'pending')
                summary[status] = summary.get(status, 0) + 1
        
        # List output directories
        if self.output_base.exists():
            summary['output_directories'] = [
                str(d) for d in self.output_base.iterdir() 
                if d.is_dir() and d.name.startswith('lesson_')
            ]
        
        return summary

# Convenience functions for easy usage
def generate_video_from_lesson(lesson_data, output_dir="output"):
    """Generate a single video from lesson data"""
    generator = AIVideoGenerator(output_base=output_dir)
    return generator.generate_single_video(lesson_data)

def generate_next_video(content_plan="content_plan.json", output_dir="output"):
    """Generate the next pending video"""
    generator = AIVideoGenerator(content_plan, output_dir)
    return generator.generate_single_video()

def batch_generate_videos(count=3, content_plan="content_plan.json", output_dir="output"):
    """Generate multiple videos in batch"""
    generator = AIVideoGenerator(content_plan, output_dir)
    return generator.generate_batch_videos(count)