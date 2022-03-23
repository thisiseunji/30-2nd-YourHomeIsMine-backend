from msilib.schema import File
import boto3, uuid
from datetime import datetime

from django.http      import JsonResponse
from django.views     import View
from django.db.models import Avg


from users.models import User
from rooms.models import Room
from .models      import Review, ReviewImage
from core.utils   import login_decorator
from core.storage import FileUpload, MyS3Client, s3_client
from my_settings  import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_URL

class ReviewView(View):   
    def get(self, request, room_id):
        try:
            limit   = int(request.GET.get('limit', 6))
            page    = int(request.GET.get('page', 1))
            offset  = (page-1) * limit           
            reviews = Room.objects.get(id=room_id).reviews.all()[offset:offset+limit]
            average = reviews.aggregate(
                Avg('accuracy'), 
                Avg('communication'),
                Avg('cleanliness'), 
                Avg('location'), 
                Avg('check_in'), 
                Avg('cost_performance')
            )
            
            result = {
                'reviews_number'  : Room.objects.get(id=room_id).reviews.all().count(),
                'star_rating'     : round(sum(average.values())/len(average), 2),
                'accuracy'        : round(average['accuracy__avg'], 2),
                'communication'   : round(average['communication__avg'], 2),
                'cleanliness'     : round(average['cleanliness__avg'], 2),
                'location'        : round(average['location__avg'], 2),
                'check_in_rating' : round(average['check_in__avg'], 2),
                'cost_performance': round(average['cost_performance__avg'], 2),
                'reviews'         : [
                    {
                        'review_id'     : review.id,
                        'nickname'      : review.user.nickname,
                        'profile_image' : review.user.profile_image,
                        'contents'      : review.content,
                        'date'          : datetime.strftime(review.created_at, '%y년 %m월').replace(' 0',' '),
                        'review_image'  : [AWS_S3_URL + review_image.image_url for review_image in review.review_images.all()]
                    } for review in reviews]
            }
            
            return JsonResponse({'message' : 'SUCCESS', 'result' : result}, status=200)

        except Room.DoesNotExist:
            return JsonResponse({'message' : 'ROOM_NOT_EXIST'}, status=400)
        
        except KeyError:
            return JsonResponse({'message' : 'KEY_ERROR'}, status=400)
        
        except ValueError:
            return JsonResponse({'message' : 'VALUE_ERROR'}, status=400)
    
    @login_decorator
    def post(self, request, room_id):
        try:
            file_handler = FileUpload(s3_client)
            
            review = Review.objects.create(
                content          = request.POST['content'],
                accuracy         = request.POST['accuracy'],
                communication    = request.POST['communication'],
                cleanliness      = request.POST['cleanliness'],
                location         = request.POST['location'],
                check_in         = request.POST['check_in'],
                cost_performance = request.POST['cost_performance'],
                user             = request.user,
                room             = Room.objects.get(id=room_id)      
            )

            review_images = request.FILES.getlist('review_images')  
                
            for image in review_images:
                file      = image
                file_name = str(uuid.uuid4()) + file.name
                file_handler.upload(file, file_name)
                
                ReviewImage.objects.create(
                    image_url = 'https://s3-yhim.s3.ap-northeast-2.amazonaws.com/' + file_name,
                    review    = review
                )
                    
            return JsonResponse({'message':'SUCCESS'}, status=201)
        
        except KeyError: 
            return JsonResponse({'message':'KEY_ERROR'}, status=400)      
    
    @login_decorator
    def delete(self, request, room_id, review_id):
        try:
            file_handler = FileUpload(s3_client)
            Review.objects.get(id=review_id, user=request.user, room_id=room_id).delete()

            for review_image in ReviewImage.objects.filter(review_id=review_id):
                file_handler.delete(review_image)

            ReviewImage.objects.filter(review_id=review_id).delete()

            return JsonResponse({'message' : 'NO_CONTENTS'}, status=204)

        except Review.DoesNotExist:
            return JsonResponse({'message' : 'REVIEW_NOT_EXIST'}, status=404)

        except KeyError:
            return JsonResponse({'message' : 'KEY_ERROR'}, status=400)

        except ValueError:
            return JsonResponse({'message' : 'VALUE_ERROR'}, status=400)