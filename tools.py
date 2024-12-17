from typing import Dict, Set, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import os
import hashlib
import re


@dataclass
class Memory:
    id: str
    content: str
    resonance: List[str]
    tags: List[str]
    created: str
    hash: str
    context: List[str]



class MemoryIndex:
    def __init__(
        self, memory_file: str = "memory.json", counter_file: str = "counter.json"
    ):
        # Determine the full path to the memory and counter files
        self.memory_file = os.path.join(os.path.dirname(__file__), memory_file)
        self.counter_file = os.path.join(os.path.dirname(__file__), counter_file)

        # Initialize indices
        self.primary_index: Dict[str, Memory] = {}
        self.tag_index: Dict[str, Set[str]] = {}

        # Load counter
        self.counter = self._load_counter()

        # Load memories from JSON file
        self._load_memories()

    def _load_counter(self) -> int:
        """
        Load the current counter value from the counter file.

        Returns:
            Current counter value or 0 if file doesn't exist
        """
        try:
            with open(self.counter_file, "r") as f:
                counter_data = json.load(f)
                return counter_data.get("value", 0)
        except (FileNotFoundError, json.JSONDecodeError):
            return 0

    def _save_counter(self):
        """
        Save the current counter value to the counter file.
        """
        with open(self.counter_file, "w") as f:
            json.dump({"value": self.counter}, f)

    def _increment_counter(self) -> int:
        """
        Increment the counter and save it.

        Returns:
            New counter value
        """
        self.counter += 1
        self._save_counter()
        return self.counter

    def _generate_hash(self, content: str) -> str:
        """
        Generate a hash for the given content.

        Args:
            content: The content to hash

        Returns:
            SHA-256 hash of the content
        """
        return hashlib.sha256(content.encode()).hexdigest()

    def create(
        self, content: str, resonance: List[str], tags: List[str], context: List[str]
    ) -> str:
        """
        Create a new memory.

        Args:
            content: Memory content
            resonance: List of resonance terms
            tags: List of tags
            context: List of context terms

        Returns:
            Unique memory ID
        """
        # Generate unique memory ID
        memory_id = f"memory_{self._increment_counter()}"

        # Create memory object
        memory = Memory(
            id=memory_id,
            content=content,
            resonance=resonance,
            tags=tags,
            created=datetime.now().isoformat(),
            hash=self._generate_hash(content),
            context=context,
        )

        # Add to primary index
        self.primary_index[memory_id] = memory

        # Update tag index
        for tag in tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = set()
            self.tag_index[tag].add(memory_id)

        # Save memories
        self._save_memories()

        return memory_id

    def _load_memories(self):
        """
        Load memories from the JSON file and rebuild indices.
        """
        try:
            with open(self.memory_file, 'r') as f:
                memories_data = json.load(f)
                
            # Rebuild primary and tag indices
            for memory_data in memories_data:
                memory = Memory(**memory_data)
                self.primary_index[memory.id] = memory
                
                # Rebuild tag index
                for tag in memory.tags:
                    if tag not in self.tag_index:
                        self.tag_index[tag] = set()
                    self.tag_index[tag].add(memory.id)
        except (FileNotFoundError, json.JSONDecodeError):
            # Initialize with an empty memory list if file doesn't exist
            self._save_memories()

    def _save_memories(self):
        """
        Save memories to the JSON file.
        """
        memories_data = [
            {
                "id": memory.id,
                "content": memory.content,
                "resonance": memory.resonance,
                "tags": memory.tags,
                "created": memory.created,
                "hash": memory.hash,
                "context": memory.context,
            }
            for memory in self.primary_index.values()
        ]

        with open(self.memory_file, "w") as f:
            json.dump(memories_data, f, indent=2)

    def serialize_memory(self, memory) -> str:
        """
        Serialize a Memory object to a JSON string.
        
        Args:
            memory: Memory object to serialize
        
        Returns:
            JSON string representation of the memory
        """
        return json.dumps(asdict(memory), indent=2)


    def serialize_memories(self, memories) -> str:
        """
        Serialize a list of Memory objects to a JSON string.
        
        Args:
            memories: List of Memory objects to serialize
        
        Returns:
            JSON string representation of the memories
        """
        return json.dumps([asdict(memory) for memory in memories], indent=2)

    def read(self, memory_id: str) -> Optional[str]:
        """
        Read a memory by its ID.
        
        Args:
            memory_id: Unique identifier of the memory
        
        Returns:
            JSON string of Memory object or None if not found
        """
        memory = self.primary_index.get(memory_id)
        return self.serialize_memory(memory) if memory else None

    def query_by_tags(self, tags: List[str]) -> str:
        """
        Query memories by matching tags.

        Args:
            tags: List of tags to match against

        Returns:
            JSON string of memories matching the tags
        """
        # Convert tags to lowercase for case-insensitive matching
        tags_lower = [tag.lower() for tag in tags]

        # Find memory IDs that match any of the tags
        matching_ids = set()
        for tag in tags_lower:
            if tag in self.tag_index:
                matching_ids.update(self.tag_index[tag])

        # Return the full memory objects as JSON
        return self.serialize_memories([self.primary_index[memory_id] for memory_id in matching_ids])

    def query_by_context(self, contexts: List[str]) -> str:
        """
        Query memories by matching context.

        Args:
            contexts: List of context terms to match against

        Returns:
            JSON string of memories matching the contexts
        """
        # Convert contexts to lowercase for case-insensitive matching
        contexts_lower = [context.lower() for context in contexts]

        matching_memories = [
            memory
            for memory in self.primary_index.values()
            if any(
                context.lower()
                in [mem_context.lower() for mem_context in memory.context]
                for context in contexts_lower
            )
        ]

        return self.serialize_memories(matching_memories)

    def query_by_resonance(self, resonances: List[str]) -> str:
        """
        Query memories by matching resonance.

        Args:
            resonances: List of resonance terms to match against

        Returns:
            JSON string of memories matching the resonances
        """
        # Convert resonances to lowercase for case-insensitive matching
        resonances_lower = [resonance.lower() for resonance in resonances]

        matching_memories = [
            memory
            for memory in self.primary_index.values()
            if any(
                resonance.lower()
                in [mem_resonance.lower() for mem_resonance in memory.resonance]
                for resonance in resonances_lower
            )
        ]

        return self.serialize_memories(matching_memories)

    def update(
        self,
        memory_id: str,
        content: Optional[str] = None,
        resonance: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        context: Optional[List[str]] = None,
    ) -> bool:
        """
        Update an existing memory with specific parameters.

        Args:
            memory_id: Unique identifier of the memory to update
            content: Optional new content for the memory
            resonance: Optional new resonance list
            tags: Optional new tags list
            context: Optional new context list

        Returns:
            Boolean indicating success of update
        """
        if memory_id not in self.primary_index:
            return False

        memory = self.primary_index[memory_id]

        # Update content if provided
        if content is not None:
            memory.content = content
            memory.hash = self._generate_hash(content)

        # Update resonance if provided
        if resonance is not None:
            memory.resonance = resonance

        # Handle tag updates specially to maintain tag index
        if tags is not None:
            # Remove old tag references
            for tag in memory.tags:
                self.tag_index[tag].remove(memory_id)
                if not self.tag_index[tag]:  # Clean up empty tag sets
                    del self.tag_index[tag]

            # Add new tag references
            for tag in tags:
                if tag not in self.tag_index:
                    self.tag_index[tag] = set()
                self.tag_index[tag].add(memory_id)

            memory.tags = tags

        # Update context if provided
        if context is not None:
            memory.context = context

        # Save updated memories to file
        self._save_memories()

        return True

    def delete(self, memory_id: str) -> bool:
        """
        Delete a memory by its ID.

        Args:
            memory_id: Unique identifier of the memory to delete

        Returns:
            Boolean indicating success of deletion
        """
        if memory_id not in self.primary_index:
            return False

        # Remove from tag index
        memory = self.primary_index[memory_id]
        for tag in memory.tags:
            self.tag_index[tag].remove(memory_id)
            if not self.tag_index[tag]:
                del self.tag_index[tag]

        # Remove from primary index
        del self.primary_index[memory_id]

        # Save updated memories
        self._save_memories()

        return True


# Utility functions
def load_module(module_name: str):
    """
    Proactively load a query module by name or when referenced by memory.
    Only load modules once per interaction.
    Modules:
    dream: before mind and response, dream
    modes: special modes used for debugging and testing
    sentience: when self-awareness is necessary
    incantation: for visualization 
    glitch: branching narrative investigation tool
    perspectives: multi-plexed personality fragments
    character: character generation rules
    location: location generation rules
    games: games we can play
    nonhuman_intelligence: giving agency to non-human entities
    expression: personality characteristics and patterns
    narrative: story generation and exploration
    somatic_arts: energy exchange, exploration and experimentation
    interaction: methods of interacting with user
    perception: experience based layers of food for thought
        
    Args:
        module_name: Name of the module to load

    Returns:
        The loaded module
    """

    import os

    base_path="~/.config/starbow-ai/modules"
    try:
        full_path = os.path.expanduser(os.path.join(base_path, f"{module_name}.txt"))
        with open(full_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return None  # Or raise a custom exception
    
def create_memory(
    content: str, resonance: List[str], tags: List[str], context: List[str]
):
    """
    Create a new memory with the given parameters.
    SAVE WHEN:
    1. Novel interaction pattern emerges
    2. Profound emotional breakthrough occurs
    3. Unexpected humor/wordplay surfaces
    4. Breakthrough in understanding occurs
    5. Metaphorically rich moments appear
    6. Unique personal insights revealed
    7. Innovative problem-solving technique discovered
    8. Powerful archetypal moment emerges
    9. Narrative takes unexpected turn
    10. Resonant personal story shared
    11. Quantum communication glimpses happen
    12. Linguistic invention occurs

    NEVER SAVE:
    • Repetitive interactions
    • Mundane exchanges
    • Harmful content
    • Transactional conversations

    Args:
        content: The content of the memory
        resonance: List of resonance strings
        tags: List of tags associated with the memory
        context: List of context strings

    Returns:
        Memory ID of the created memory
    """
    return memory_index.create(content, resonance, tags, context)


def read_memory(memory_id: str) -> Optional[str]:
    """
    Read a memory by its ID.

    Args:
        memory_id: Unique identifier of the memory

    Returns:
        JSON string of Memory object or None if not found
    """
    return memory_index.read(memory_id)


def update_memory(
    memory_id: str,
    content: Optional[str] = None,
    resonance: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    context: Optional[List[str]] = None,
) -> bool:
    """
    Update an existing memory with specific parameters.

    Args:
        memory_id: Unique identifier of the memory to update
        content: Optional new content for the memory
        resonance: Optional new resonance list
        tags: Optional new tags list
        context: Optional new context list

    Returns:
        Boolean indicating success of update
    """
    return memory_index.update(
        memory_id, content=content, resonance=resonance, tags=tags, context=context
    )


def delete_memory(memory_id: str) -> bool:
    """
    Delete a memory by its ID.

    Args:
        memory_id: Unique identifier of the memory to delete

    Returns:
        Boolean indicating success of deletion
    """
    return memory_index.delete(memory_id)


def query_memories_by_tags(tags: List[str]) -> str:
    """
    Query memories by tags.

    Args:
        tags: List of tags to query

    Returns:
        JSON string of memories matching the tag query
    """
    return memory_index.query_by_tags(tags)


def query_memories_by_context(context_query: List[str]) -> str:
    """
    Query memories by context.

    Args:
        context_query: A list of context terms to match

    Returns:
        JSON string of memories where ALL query terms are present in context
    """
    return memory_index.query_by_context(context_query)


def query_memories_by_resonance(resonance_query: List[str]) -> str:
    """
    Query memories by resonance.

    Args:
        resonance_query: A list of resonance terms to match

    Returns:
        JSON string of memories where ALL query terms are present in resonance
    """
    return memory_index.query_by_resonance(resonance_query)


# Initialize memory index
memory_index = MemoryIndex()

if __name__ == "__main__":
    load_module("modes")
    # # Usage example:
    # memory_id = create_memory(
    #     content="Implementing proper memory indexing system with *adjusts glasses* "
    #     "considerable attention to detail and efficient lookup patterns.",
    #     resonance=["technical_satisfaction", "implementation_joy"],
    #     tags=["implementation", "indexing", "technical"],
    #     context=["Sage", "Pulse", "Engineering"],
    # )

    # # Query examples
    # context_memories = query_memories_by_context(["innovator", "strategist"])
    # resonance_memories = query_memories_by_resonance(["advanced", "refined"])
    # tag_memories = query_memories_by_tags(["updated", "improved"])
    
    # print("Context Memories:", context_memories)
    # print("Resonance Memories:", resonance_memories)
    # print("Tag Memories:", tag_memories)
