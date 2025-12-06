"""
Seed Rate Limits Script
Initialize or update rate limit configuration
"""

import asyncio
import asyncpg
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from datetime import datetime

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def get_rate_limit_config(conn):
    """Get current rate limit configuration"""
    query = "SELECT * FROM rate_limit_config ORDER BY created_at DESC LIMIT 1"
    return await conn.fetchrow(query)


async def update_rate_limits(
    burst_limit: int = 10,
    per_chat_limit: int = 50,
    per_hour_limit: int = 150,
    per_day_limit: int = 1000
):
    """Update rate limit configuration"""
    conn = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB
    )
    
    try:
        # Check if config exists
        existing_config = await get_rate_limit_config(conn)
        
        if existing_config:
            # Update existing config
            query = """
                UPDATE rate_limit_config
                SET 
                    burst_limit_per_minute = $1,
                    per_chat_limit = $2,
                    per_hour_limit = $3,
                    per_day_limit = $4,
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = 'seed_script'
                WHERE config_id = $5
                RETURNING *
            """
            
            config = await conn.fetchrow(
                query,
                burst_limit,
                per_chat_limit,
                per_hour_limit,
                per_day_limit,
                existing_config['config_id']
            )
            
            logger.info("Rate limit configuration UPDATED")
        else:
            # Create new config
            query = """
                INSERT INTO rate_limit_config (
                    burst_limit_per_minute,
                    per_chat_limit,
                    per_hour_limit,
                    per_day_limit,
                    updated_by
                ) VALUES ($1, $2, $3, $4, 'seed_script')
                RETURNING *
            """
            
            config = await conn.fetchrow(
                query,
                burst_limit,
                per_chat_limit,
                per_hour_limit,
                per_day_limit
            )
            
            logger.info("Rate limit configuration CREATED")
        
        # Display configuration
        logger.info("=" * 80)
        logger.info("RATE LIMIT CONFIGURATION")
        logger.info("=" * 80)
        logger.info(f"Config ID: {config['config_id']}")
        logger.info(f"Burst (per minute): {config['burst_limit_per_minute']}")
        logger.info(f"Per Chat: {config['per_chat_limit']}")
        logger.info(f"Per Hour: {config['per_hour_limit']}")
        logger.info(f"Per Day: {config['per_day_limit']}")
        logger.info(f"Updated At: {config['updated_at']}")
        logger.info(f"Updated By: {config['updated_by']}")
        logger.info("=" * 80)
        
    finally:
        await conn.close()


async def show_current_config():
    """Display current rate limit configuration"""
    conn = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB
    )
    
    try:
        config = await get_rate_limit_config(conn)
        
        if not config:
            logger.warning("No rate limit configuration found")
            return
        
        logger.info("=" * 80)
        logger.info("CURRENT RATE LIMIT CONFIGURATION")
        logger.info("=" * 80)
        logger.info(f"Config ID: {config['config_id']}")
        logger.info(f"Burst (per minute): {config['burst_limit_per_minute']}")
        logger.info(f"Per Chat: {config['per_chat_limit']}")
        logger.info(f"Per Hour: {config['per_hour_limit']}")
        logger.info(f"Per Day: {config['per_day_limit']}")
        logger.info(f"Whitelisted Users: {len(config['whitelisted_users']) if config['whitelisted_users'] else 0}")
        logger.info(f"Updated At: {config['updated_at']}")
        logger.info(f"Updated By: {config['updated_by'] or 'N/A'}")
        logger.info("=" * 80)
    
    finally:
        await conn.close()


async def interactive_update():
    """Interactive rate limit update"""
    logger.info("=" * 80)
    logger.info("UPDATE RATE LIMITS")
    logger.info("=" * 80)
    logger.info("\nCurrent defaults:")
    logger.info("  Burst: 10 prompts/minute")
    logger.info("  Per Chat: 50 prompts/chat")
    logger.info("  Per Hour: 150 prompts/hour")
    logger.info("  Per Day: 1000 prompts/day")
    logger.info("=" * 80)
    
    # Get new limits
    try:
        burst = int(input("\nBurst limit (per minute) [10]: ").strip() or "10")
        per_chat = int(input("Per chat limit [50]: ").strip() or "50")
        per_hour = int(input("Per hour limit [150]: ").strip() or "150")
        per_day = int(input("Per day limit [1000]: ").strip() or "1000")
        
        # Validate
        if burst <= 0 or per_chat <= 0 or per_hour <= 0 or per_day <= 0:
            logger.error("All limits must be positive numbers")
            return False
        
        # Confirm
        logger.info("\n" + "=" * 80)
        logger.info("CONFIRM NEW RATE LIMITS")
        logger.info("=" * 80)
        logger.info(f"Burst (per minute): {burst}")
        logger.info(f"Per Chat: {per_chat}")
        logger.info(f"Per Hour: {per_hour}")
        logger.info(f"Per Day: {per_day}")
        logger.info("=" * 80)
        
        confirm = input("\nUpdate rate limits? (Y/n): ").strip().lower()
        
        if confirm == 'n':
            logger.info("Update cancelled")
            return False
        
        # Update
        await update_rate_limits(burst, per_chat, per_hour, per_day)
        return True
        
    except ValueError:
        logger.error("Invalid input. Please enter numbers only.")
        return False


async def main():
    """Main function"""
    try:
        logger.info("=" * 80)
        logger.info("KUBERA RATE LIMITS SEEDER")
        logger.info("=" * 80)
        logger.info(f"Database: {settings.POSTGRES_DB}")
        logger.info(f"Host: {settings.POSTGRES_HOST}")
        logger.info("=" * 80)
        
        # Check command line arguments
        if len(sys.argv) > 1:
            command = sys.argv[1]
            
            if command == "show":
                await show_current_config()
                return
            
            elif command == "update":
                if len(sys.argv) < 6:
                    logger.error("Usage: python scripts/seed_rate_limits.py update <burst> <per_chat> <per_hour> <per_day>")
                    sys.exit(1)
                
                burst = int(sys.argv[2])
                per_chat = int(sys.argv[3])
                per_hour = int(sys.argv[4])
                per_day = int(sys.argv[5])
                
                await update_rate_limits(burst, per_chat, per_hour, per_day)
                return
        
        # Show current config
        await show_current_config()
        
        # Interactive mode
        logger.info("\n")
        update_input = input("Update rate limits? (y/N): ").strip().lower()
        
        if update_input == 'y':
            logger.info("\n")
            await interactive_update()
        
        logger.info("\n" + "=" * 80)
        logger.info("RATE LIMIT CONFIGURATION COMPLETE")
        logger.info("=" * 80)
        logger.info("\nNOTES:")
        logger.info("- Rate limits are enforced in 4 levels (fail-fast)")
        logger.info("- Admins can override limits per user")
        logger.info("- Admins can whitelist users (no limits)")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"\nRATE LIMIT SEEDING FAILED")
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
