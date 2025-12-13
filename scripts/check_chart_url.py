import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check_chart_url_column():
    """Check if chart_url column exists in messages table"""
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    
    try:
        # Check if chart_url column exists
        row = await conn.fetchrow("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'messages' AND column_name = 'chart_url'
        """)
        
        if row:
            print(f"✅ chart_url column EXISTS - Type: {row['data_type']}")
        else:
            print("❌ chart_url column DOES NOT EXIST")
            print("Running migration to add chart_url column...")
            await conn.execute("""
                ALTER TABLE messages 
                ADD COLUMN IF NOT EXISTS chart_url TEXT;
            """)
            print("✅ Migration completed - chart_url column added")
        
        # Check a sample message to see if chart_url has any values
        sample = await conn.fetchrow("""
            SELECT message_id, chart_url 
            FROM messages 
            WHERE chart_url IS NOT NULL 
            LIMIT 1
        """)
        
        if sample:
            print(f"✅ Found message with chart_url: {sample['chart_url'][:50]}...")
        else:
            print("📋 No messages with chart_url saved yet")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_chart_url_column())
