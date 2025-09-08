from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserRegistrationSerializer, UserSerializer
from .models import UserLoginInformations

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """Register a new user"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    """Get current user profile"""
    serializer = UserSerializer(request.user)
    uli = get_user_login_informations(request.user)
    ip_addr = request.META.get('REMOTE_ADDR')
    uli.increment_daily_login_count(ip_addr)

    print('*' * 50)
    print(uli.get_last_login_info())

    data = dict(serializer.data)

    data.update(
        uli.get_last_login_info()
    )
    print(type(data))
    print(data)
    print('*' * 50)
    return Response(data)


def get_user_login_informations(user):
    uli, _cr = UserLoginInformations.objects.get_or_create(user=user)
    return uli