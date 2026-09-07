# app/services/instagram.py
import os
import re
import uuid
from datetime import datetime

import instaloader
from app.core.cloudinary import upload_to_cloudinary
from fastapi import HTTPException


class InstagramService:
    def __init__(self):
        self.loader = instaloader.Instaloader()

    async def download_and_upload_image(
        self, instagram_url: str, user_id: str, image_index: int = 0
    ):
        """
        Download image from Instagram post and upload to Cloudinary.
        Video/reel URLs are supported by saving the cover image.
        """
        temp_filename = None
        try:
            # Extract shortcode from URL (post/reel/tv)
            match = re.search(r"instagram\.com/(p|reel|tv)/([^/?#]+)", instagram_url)
            if not match:
                raise HTTPException(status_code=400, detail="Invalid Instagram URL")

            shortcode = match.group(2).strip("/")

            # Get post metadata
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)

            # Handle carousels by selecting a specific item (default 0)
            if post.typename == "GraphSidecar":
                nodes = list(post.get_sidecar_nodes())
                if not nodes:
                    raise HTTPException(
                        status_code=400, detail="Carousel has no media items."
                    )
                if image_index < 0 or image_index >= len(nodes):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Carousel image_index out of range. Must be between 0 and {len(nodes) - 1}.",
                    )
                selected = nodes[image_index]
                media_url = selected.display_url
                owner_username = post.owner_username
            else:
                media_url = post.url
                owner_username = post.owner_username

            # Create temp directory if not exists
            temp_dir = f"temp/{user_id}"
            os.makedirs(temp_dir, exist_ok=True)

            # Generate unique filename
            temp_filename = f"{temp_dir}/{uuid.uuid4()}.jpg"

            # Download image (for videos this is the display/cover image)
            self.loader.download_pic(
                filename=temp_filename, url=media_url, date=post.date_utc
            )

            # Upload to Cloudinary
            result = upload_to_cloudinary(temp_filename, user_id, owner_username)

            return {
                "success": True,
                "image_url": result["secure_url"],
                "public_id": result["public_id"],
                "instagram_username": owner_username,
                "message": "Image successfully imported from Instagram",
            }

        except instaloader.exceptions.InstaloaderException as e:
            raise HTTPException(status_code=400, detail=f"Instagram error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
        finally:
            # Clean up temp file
            if temp_filename and os.path.exists(temp_filename):
                os.remove(temp_filename)
