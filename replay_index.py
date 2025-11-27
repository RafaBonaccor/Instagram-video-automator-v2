"""
Replay Index System for Efficient Large File Handling

This module provides efficient indexing and lookup for replay files
that may contain thousands of events (mostly m_move).
"""

import bisect
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class ActionEvent:
    """Represents a significant (non-move) event with its index"""
    index: int          # Original position in events list
    t: float           # Timestamp
    type: str          # Event type
    data: dict         # Event data
    
    def __repr__(self):
        return f"ActionEvent(idx={self.index}, t={self.t:.2f}s, type={self.type})"


@dataclass
class MoveSegment:
    """Represents a continuous segment of mouse moves"""
    start_idx: int     # First m_move index
    end_idx: int       # Last m_move index (inclusive)
    start_t: float     # Start timestamp
    end_t: float       # End timestamp
    count: int         # Number of moves in segment
    
    def __repr__(self):
        return f"MoveSegment({self.count} moves: idx {self.start_idx}-{self.end_idx}, t {self.start_t:.2f}-{self.end_t:.2f}s)"


class ReplayIndex:
    """
    Efficient indexing for large replay files.
    
    Separates actionable events (clicks, keys, scrolls) from mouse moves,
    allowing quick lookup without scanning thousands of m_move entries.
    """
    
    def __init__(self, events):
        """
        Build index from events list.
        
        Args:
            events: List of Event objects from Macro
        """
        self.events = events
        self.action_events: List[ActionEvent] = []
        self.move_segments: List[MoveSegment] = []
        self.total_moves = 0
        self._build_index()
    
    def _build_index(self):
        """Build index of significant events and move segments"""
        if not self.events:
            return
        
        current_move_segment = None
        
        for i, event in enumerate(self.events):
            if event.type == 'm_move':
                # Track mouse move segments
                self.total_moves += 1
                if current_move_segment is None:
                    # Start new segment
                    current_move_segment = {
                        'start_idx': i,
                        'start_t': event.t,
                        'count': 1,
                        'end_idx': i,
                        'end_t': event.t
                    }
                else:
                    # Continue segment
                    current_move_segment['count'] += 1
                    current_move_segment['end_idx'] = i
                    current_move_segment['end_t'] = event.t
            else:
                # Close any open move segment
                if current_move_segment is not None:
                    self.move_segments.append(MoveSegment(
                        start_idx=current_move_segment['start_idx'],
                        end_idx=current_move_segment['end_idx'],
                        start_t=current_move_segment['start_t'],
                        end_t=current_move_segment['end_t'],
                        count=current_move_segment['count']
                    ))
                    current_move_segment = None
                
                # Index this action event
                self.action_events.append(ActionEvent(
                    index=i,
                    t=event.t,
                    type=event.type,
                    data=event.data
                ))
        
        # Close final move segment if exists
        if current_move_segment is not None:
            self.move_segments.append(MoveSegment(
                start_idx=current_move_segment['start_idx'],
                end_idx=current_move_segment['end_idx'],
                start_t=current_move_segment['start_t'],
                end_t=current_move_segment['end_t'],
                count=current_move_segment['count']
            ))
    
    def get_action_at_index(self, event_idx: int) -> Optional[ActionEvent]:
        """
        Get the action event at or before the given event index.
        
        Args:
            event_idx: Index in original events list
            
        Returns:
            ActionEvent if found, None otherwise
        """
        # Binary search for action at or before this index
        for action in reversed(self.action_events):
            if action.index <= event_idx:
                return action
        return None
    
    def get_nearby_actions(self, event_idx: int, radius: int = 10) -> List[ActionEvent]:
        """
        Get actionable events near the given index.
        
        Args:
            event_idx: Current position in events list
            radius: Number of actions to include before/after
            
        Returns:
            List of ActionEvent objects
        """
        # Find closest action
        closest_idx = None
        for i, action in enumerate(self.action_events):
            if action.index >= event_idx:
                closest_idx = i
                break
        
        if closest_idx is None:
            # We're past all actions, return last few
            return self.action_events[-radius:]
        
        # Return window around closest
        start = max(0, closest_idx - radius)
        end = min(len(self.action_events), closest_idx + radius + 1)
        return self.action_events[start:end]
    
    def get_events_in_time_range(self, start_t: float, end_t: float) -> List[ActionEvent]:
        """
        Get all action events within a time range.
        
        Args:
            start_t: Start time (seconds)
            end_t: End time (seconds)
            
        Returns:
            List of ActionEvent objects in range
        """
        result = []
        for action in self.action_events:
            if start_t <= action.t <= end_t:
                result.append(action)
        return result
    
    def filter_by_type(self, event_types: List[str]) -> List[ActionEvent]:
        """
        Filter action events by type.
        
        Args:
            event_types: List of event types to include (e.g., ['m_down', 'k_down'])
            
        Returns:
            Filtered list of ActionEvent objects
        """
        return [action for action in self.action_events if action.type in event_types]
    
    def get_statistics(self) -> dict:
        """
        Get statistics about the indexed replay.
        
        Returns:
            Dictionary with stats
        """
        return {
            'total_events': len(self.events),
            'action_events': len(self.action_events),
            'total_moves': self.total_moves,
            'move_segments': len(self.move_segments),
            'compression_ratio': len(self.action_events) / len(self.events) if self.events else 0,
            'duration': self.events[-1].t if self.events else 0
        }
    
    def __repr__(self):
        stats = self.get_statistics()
        return (f"ReplayIndex({stats['total_events']} events: "
                f"{stats['action_events']} actions, "
                f"{stats['total_moves']} moves in {stats['move_segments']} segments)")
