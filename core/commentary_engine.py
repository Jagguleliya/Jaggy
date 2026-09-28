import os
import logging
from typing import Dict, Any
import yaml
from core.content_generator import ContentGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CommentaryEngine:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config_path = config_path
        self._load_config()

    def _load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
            else:
                self.config = {}
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.config = {}

    def generate_commentary(self, clip_info: Dict[str, Any], content_generator: ContentGenerator) -> Dict[str, Any]:
        logger.info(f"Generating commentary for clip: {clip_info.get('title')}")
        title = clip_info.get('title', '')
        context = f"Source: {clip_info.get('source', 'Unknown')}, Score: {clip_info.get('score', 0)}. URL: {clip_info.get('url', '')}"
        
        commentary = content_generator.generate_commentary(clip_context=context, clip_title=title)
        return commentary

    def _calculate_timing(self, narration_text: str, clip_duration: float) -> Dict[str, float]:
        # Approximate reading speed: ~2.5 words per second (150 wpm)
        words = narration_text.split()
        num_words = len(words)
        total_speaking_time = num_words / 2.5
        
        # Ensure commentary is at least 60% of the video value
        if total_speaking_time < (clip_duration * 1.5):
            total_speaking_time = max(total_speaking_time, clip_duration * 1.5)
            
        timing = {
            'total_speaking_time': total_speaking_time,
            'hook_duration': min(total_speaking_time * 0.2, 5.0),
            'context_duration': total_speaking_time * 0.4,
            'fact_duration': total_speaking_time * 0.3,
            'cta_duration': total_speaking_time * 0.1
        }
        return timing

    def build_video_script(self, clip_info: Dict[str, Any], commentary: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Building structured video script from commentary...")
        
        clip_duration = clip_info.get('duration', 10.0)
        script_text = commentary.get('commentary_script', 'Wow, look at this!')
        
        timing = self._calculate_timing(script_text, clip_duration)
        
        segments = []
        current_time = 0.0
        
        # 1. Hook
        hook_end = current_time + timing['hook_duration']
        segments.append({
            'text': "Wait for it...",
            'start_time': current_time,
            'end_time': hook_end,
            'visual_type': 'zoom_moment'
        })
        current_time = hook_end
        
        # 2. Main Context (Play Clip)
        context_end = current_time + timing['context_duration']
        segments.append({
            'text': script_text[:max(len(script_text)//2, 1)],
            'start_time': current_time,
            'end_time': context_end,
            'visual_type': 'clip_play'
        })
        current_time = context_end
        
        # 3. Fact/Educational
        fact_end = current_time + timing['fact_duration']
        facts = commentary.get('educational_facts', ['Did you know?'])
        fact_text = facts[0] if isinstance(facts, list) and facts else str(facts)
        segments.append({
            'text': fact_text,
            'start_time': current_time,
            'end_time': fact_end,
            'visual_type': 'stock_footage'
        })
        current_time = fact_end
        
        # 4. CTA
        cta_end = current_time + timing['cta_duration']
        segments.append({
            'text': 'Subscribe for more!',
            'start_time': current_time,
            'end_time': cta_end,
            'visual_type': 'text_overlay'
        })
        
        raw_title = clip_info.get('title', 'Unbelievable Viral Moment')
        clean_title = raw_title.split('#')[0].strip()[:65]
        final_title = commentary.get('viral_title') or clean_title or "You Won't Believe What Happened Here!"

        return {
            'title': final_title,
            'narration': script_text,
            'top_banner_text': commentary.get('top_banner_text', ''),
            'pinned_comment': commentary.get('pinned_comment', ''),
            'segments': segments,
            'total_duration': cta_end,
            'metadata': clip_info,
            'commentary_data': commentary,
            'tags': ['shorts', 'viral', 'unbelievable', 'reaction', 'mindblowing', 'trending'],
            'mood': commentary.get('mood', 'dramatic'),
            'pexels_search_term': clean_title
        }

if __name__ == "__main__":
    engine = CommentaryEngine()
    cg = ContentGenerator()
    mock_clip = {'title': 'Incredible juggling dog', 'source': 'reddit', 'score': 5000, 'duration': 8.0}
    
    # Mocking for standalone test to prevent actual API call
    cg.generate_commentary = lambda ctx, title, **k: {
        'commentary_script': 'This is an amazing demonstration of skill.',
        'educational_facts': ['Dogs have great hand-eye coordination.'],
        'visual_annotations': ['Highlight the paws']
    }
    
    comm = engine.generate_commentary(mock_clip, cg)
    script = engine.build_video_script(mock_clip, comm)
    print("Video Script Total Duration:", script['total_duration'])
    print("Segments count:", len(script['segments']))
