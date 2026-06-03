class CapturedFile:
    """Wrapper for file data to allow reading after original message deletion."""
    def __init__(self, data: bytes, filename: str):
        self.data = data
        self.filename = filename

    async def read(self) -> bytes:
        return self.data

# Constants for seed generation
SEED_MIN = 10**14
SEED_MAX = 10**15 - 1

# Discord slash commands choices maximum count limit
DISCORD_MAX_CHOICES = 25
