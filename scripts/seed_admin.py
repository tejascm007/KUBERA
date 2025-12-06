"""
Seed Admin User Script
Creates the first admin user for system management
"""

import asyncio
import asyncpg
import sys
from pathlib import Path
import getpass

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from datetime import datetime

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def check_admin_exists(conn, email: str) -> bool:
    """Check if admin with email already exists"""
    query = "SELECT 1 FROM admins WHERE email = $1"
    result = await conn.fetchval(query, email)
    return result is not None


async def create_admin_user(email: str, full_name: str, is_super_admin: bool = True):
    """Create admin user"""
    conn = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB
    )
    
    try:
        # Check if admin exists
        if await check_admin_exists(conn, email):
            logger.warning(f"Admin with email '{email}' already exists")
            return False
        
        # Insert admin
        query = """
            INSERT INTO admins (email, full_name, is_super_admin, is_active)
            VALUES ($1, $2, $3, TRUE)
            RETURNING admin_id, email, full_name, is_super_admin, created_at
        """
        
        admin = await conn.fetchrow(query, email, full_name, is_super_admin)
        
        logger.info("=" * 80)
        logger.info("ADMIN USER CREATED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info(f"Admin ID: {admin['admin_id']}")
        logger.info(f"Email: {admin['email']}")
        logger.info(f"Full Name: {admin['full_name']}")
        logger.info(f"Super Admin: {admin['is_super_admin']}")
        logger.info(f"Created At: {admin['created_at']}")
        logger.info("=" * 80)
        
        return True
    
    finally:
        await conn.close()


async def list_admins():
    """List all admin users"""
    conn = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB
    )
    
    try:
        query = """
            SELECT admin_id, email, full_name, is_super_admin, is_active, created_at
            FROM admins
            ORDER BY created_at ASC
        """
        
        admins = await conn.fetch(query)
        
        if not admins:
            logger.info("No admin users found")
            return
        
        logger.info("=" * 80)
        logger.info(f"ADMIN USERS ({len(admins)})")
        logger.info("=" * 80)
        
        for admin in admins:
            logger.info(f"\nAdmin ID: {admin['admin_id']}")
            logger.info(f"Email: {admin['email']}")
            logger.info(f"Full Name: {admin['full_name']}")
            logger.info(f"Super Admin: {'Yes' if admin['is_super_admin'] else 'No'}")
            logger.info(f"Active: {'Yes' if admin['is_active'] else 'No'}")
            logger.info(f"Created: {admin['created_at']}")
            logger.info("-" * 80)
    
    finally:
        await conn.close()


async def interactive_create():
    """Interactive admin creation"""
    logger.info("=" * 80)
    logger.info("CREATE ADMIN USER")
    logger.info("=" * 80)
    
    # Get email
    email = input("\nEnter admin email: ").strip()
    
    if not email:
        logger.error("Email is required")
        return False
    
    # Validate email format
    if '@' not in email or '.' not in email:
        logger.error("Invalid email format")
        return False
    
    # Get full name
    full_name = input("Enter full name: ").strip()
    
    if not full_name:
        logger.error("Full name is required")
        return False
    
    # Ask if super admin
    is_super_admin_input = input("Make super admin? (y/N): ").strip().lower()
    is_super_admin = is_super_admin_input == 'y'
    
    # Confirm
    logger.info("\n" + "=" * 80)
    logger.info("CONFIRM ADMIN DETAILS")
    logger.info("=" * 80)
    logger.info(f"Email: {email}")
    logger.info(f"Full Name: {full_name}")
    logger.info(f"Super Admin: {'Yes' if is_super_admin else 'No'}")
    logger.info("=" * 80)
    
    confirm = input("\nCreate admin user? (Y/n): ").strip().lower()
    
    if confirm == 'n':
        logger.info("Admin creation cancelled")
        return False
    
    # Create admin
    await create_admin_user(email, full_name, is_super_admin)
    return True


async def main():
    """Main function"""
    try:
        logger.info("=" * 80)
        logger.info("KUBERA ADMIN SEEDER")
        logger.info("=" * 80)
        logger.info(f"Database: {settings.POSTGRES_DB}")
        logger.info(f"Host: {settings.POSTGRES_HOST}")
        logger.info("=" * 80)
        
        # Check command line arguments
        if len(sys.argv) > 1:
            command = sys.argv[1]
            
            if command == "list":
                await list_admins()
                return
            
            elif command == "create":
                if len(sys.argv) < 4:
                    logger.error("Usage: python scripts/seed_admin.py create <email> <full_name> [super_admin]")
                    sys.exit(1)
                
                email = sys.argv[2]
                full_name = sys.argv[3]
                is_super_admin = sys.argv[4].lower() == 'true' if len(sys.argv) > 4 else True
                
                await create_admin_user(email, full_name, is_super_admin)
                return
        
        # Interactive mode
        await interactive_create()
        
        # Ask to list admins
        logger.info("\n")
        list_admins_input = input("List all admin users? (Y/n): ").strip().lower()
        
        if list_admins_input != 'n':
            logger.info("\n")
            await list_admins()
        
        logger.info("\n" + "=" * 80)
        logger.info("ADMIN SEEDING COMPLETE")
        logger.info("=" * 80)
        logger.info("\nNOTES:")
        logger.info("- Admin login uses OTP-based authentication")
        logger.info("- Use POST /admin/login/send-otp to get OTP")
        logger.info("- Use POST /admin/login/verify-otp to login")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"\nADMIN SEEDING FAILED")
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
