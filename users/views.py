import json, jwt, requests, datetime

from django.views     import View
from django.http      import JsonResponse

from rooms.models import Room
from users.models import User, Wishlist, WishlistRoom
from core.utils   import login_decorator
from my_settings  import SECRET_KEY, ALGORITHM

class KakaoSignIn(View):
    def get(self, request):
        try:
            kakao_token = request.headers.get("Authorization")
            
            if kakao_token == None:
                return JsonResponse({"message":"INVALID_ACCESS_TOKEN"}, status=401)
            
            profile_request = requests.get(
                "https://kapi.kakao.com/v2/user/me",
                headers = {"Authorization": f"Bearer {kakao_token}"},
                timeout = 2
            )      
  
            profile_json  = profile_request.json()
            email         = profile_json.get("kakao_account").get("email", None)
            nickname      = profile_json.get("properties").get("nickname")
            profile_image = profile_json.get("kakao_account").get("profile").get("profile_image_url", None)
            gender        = profile_json.get("kakao_account").get("gender", None)
            kakao_id      = profile_json.get("id")
            
            if email is None:
                return JsonResponse({'message': 'EMAIL_REQUIRED'}, status = 405)
            
            if kakao_id is None:
                return JsonResponse({"message":"KAKAO_TOKEN_ERROR"}, status=403)
            
            user, is_created = User.objects.get_or_create(
                kakao_id      = kakao_id,
                defaults={
                    'email'         : email,
                    'nickname'      : nickname,
                    'profile_image' : profile_image,
                    'gender'        : gender
                }
            )
                
            payload = {
                'user_id' : user.id, 
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            }    
            access_token = jwt.encode(payload, SECRET_KEY, ALGORITHM)
           
            results = {
                'email'         : email,
                'nickname'      : nickname,
                'profile_image' : profile_image,
                'gender'        : gender,
                'kakao_id'      : kakao_id
            }               
    
            return JsonResponse({
                    'message'   : 'SUCCESS',
                    'token'     : access_token,
                    'results'   : results
                }, status = 201)                                    

        except AttributeError:
            return JsonResponse({'message' : 'CANNOT_GET_ATTRIBUTE'}, status = 400)
            
        except jwt.ExpiredSignatureError:
            return JsonResponse({'message' : 'EXPIRED_TOKEN'}, status = 400)  


class ToggleRoom(View):
    @login_decorator
    def post(self, request):
        try:
            data = json.loads(request.body)
            rooms = Room.objects.get(id=data["room_id"])
            user_id = request.user.id

            the_list, created = Wishlist.objects.get_or_create(
                user_id=user_id,
                name=data["name"]
            )
            if created == False:
                the_list.delete()                
                return JsonResponse({'message' : 'UNLIKED'}, status = 204)
            
            if created == True:
                WishlistRoom.objects.create(
                    room_id = rooms.id,
                    wishlist_id = the_list.id
                )
                return  JsonResponse({'message' : 'LIKED'}, status = 201)
            
        except KeyError:
            return JsonResponse({'message' : 'KEY_ERROR'}, status = 400)        
        except Room.DoesNotExist:
            return JsonResponse({'message' : 'ROOM_DOES_NOT_EXIST'}, status = 400)

