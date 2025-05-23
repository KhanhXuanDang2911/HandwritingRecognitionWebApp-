import traceback

from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import status, viewsets, filters
from django.shortcuts import get_object_or_404
from .models import User, History
from .serializers import UserSerializer, HistorySerializer
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from .utils import create_response
# Thêm vào phần import
from django.db import IntegrityError, models
from rest_framework.exceptions import ValidationError
from .utils import create_response, format_validation_errors
from .permissions import IsAuthenticated, IsAdmin, AllowAny, IsOwnerOrAdmin, CanCreateHistory
from .authentication import extract_token, validate_token
from rest_framework.response import Response
from django.http import HttpResponse, JsonResponse
from gtts import gTTS
import io
import os
import tempfile
from pydub import AudioSegment
import uuid
import json  # Thêm dòng này

# Frontend views
def home(request):
    return render(request, 'myapp/home.html')


def profile(request):
    return render(request, 'myapp/profile.html')


def history(request):
    return render(request, 'myapp/history.html')


def myadmin(request):
    return render(request, 'myapp/admin.html')


def history_detail(request):
    return render(request, 'myapp/history_detail.html')


def login(request):
    return render(request, 'myapp/login.html')


def register(request):
    return render(request, 'myapp/register.html')

def contact(request):
    return render(request, 'myapp/contact.html')


# API Pagination
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


# API ViewSets
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'full_name']
    ordering_fields = ['id', 'username', 'email', 'role', 'status']

    # permission_classes = [AllowAny]
    def get_permissions(self):
        """
        Override to set permissions based on action
        """
        if self.action == 'create':
            # Allow anyone to register
            return [AllowAny()]
        elif self.action == 'list':
            # Only admin can list all users
            return [IsAdmin()]
        elif self.action in ['update', 'partial_update', 'destroy', 'retrieve']:
            # Admin có toàn quyền, user chỉ có quyền với tài khoản của mình
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        else:
            # Other actions require authentication
            return [IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Apply search filter if provided
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                models.Q(username__icontains=search) |
                models.Q(email__icontains=search) |
                models.Q(full_name__icontains=search)
            )

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            result = self.get_paginated_response(serializer.data)
            data = result.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data

        return create_response(
            data=data,
            message="Lấy danh sách người dùng thành công",
            status_code=status.HTTP_200_OK
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return create_response(
            data=serializer.data,
            message=f"Lấy thông tin người dùng {instance.username} thành công",
            status_code=status.HTTP_200_OK
        )

    # Cập nhật phương thức create trong UserViewSet
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            if serializer.is_valid(raise_exception=True):
                self.perform_create(serializer)
                return create_response(
                    data=serializer.data,
                    message="Tạo người dùng mới thành công",
                    status_code=status.HTTP_201_CREATED
                )
        except ValidationError as e:
            return create_response(
                message="Lỗi khi tạo người dùng",
                errors=format_validation_errors(e.detail),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except IntegrityError as e:
            errors = {}
            if 'username' in str(e):
                errors['username'] = ["Tên đăng nhập này đã tồn tại"]
            elif 'email' in str(e):
                errors['email'] = ["Email này đã tồn tại"]
            else:
                errors['detail'] = ["Lỗi dữ liệu, vui lòng kiểm tra lại thông tin"]

            return create_response(
                message="Lỗi dữ liệu",
                errors=errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return create_response(
                message="Đã xảy ra lỗi không mong muốn",
                errors={"detail": [str(e)]},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # Cập nhật phương thức update trong UserViewSet
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        try:
            if serializer.is_valid(raise_exception=True):
                self.perform_update(serializer)
                return create_response(
                    data=serializer.data,
                    message=f"Cập nhật thông tin người dùng {instance.username} thành công",
                    status_code=status.HTTP_200_OK
                )
        except ValidationError as e:
            return create_response(
                message="Lỗi khi cập nhật thông tin người dùng",
                errors=format_validation_errors(e.detail),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except IntegrityError as e:
            errors = {}
            if 'username' in str(e):
                errors['username'] = ["Tên đăng nhập này đã tồn tại"]
            elif 'email' in str(e):
                errors['email'] = ["Email này đã tồn tại"]
            else:
                errors['detail'] = ["Lỗi dữ liệu, vui lòng kiểm tra lại thông tin"]

            return create_response(
                message="Lỗi dữ liệu",
                errors=errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return create_response(
                message="Đã xảy ra lỗi không mong muốn",
                errors={"detail": [str(e)]},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        username = instance.username
        self.perform_destroy(instance)
        return create_response(
            message=f"Xóa người dùng {username} thành công",
            status_code=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'])
    def histories(self, request, pk=None):
        """Lấy lịch sử của một người dùng cụ thể"""
        user = self.get_object()
        histories = History.objects.filter(id_user=user)
        page = self.paginate_queryset(histories)

        if page is not None:
            serializer = HistorySerializer(page, many=True)
            result = self.get_paginated_response(serializer.data)
            data = result.data
        else:
            serializer = HistorySerializer(histories, many=True)
            data = serializer.data

        return create_response(
            data=data,
            message=f"Lấy lịch sử của người dùng {user.username} thành công",
            status_code=status.HTTP_200_OK
        )


class HistoryViewSet(viewsets.ModelViewSet):
    queryset = History.objects.all()
    serializer_class = HistorySerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['result']
    ordering_fields = ['id', 'created_at']

    def get_permissions(self):
        """
        Override to set permissions based on action
        """
        if self.action == 'list':
            # Only admin can list all histories
            return [IsAdmin()]
        elif self.action == 'create':
            return [IsAuthenticated(), CanCreateHistory()]
        elif self.action == 'by_user':
            # Cho phép admin xem tất cả, user chỉ xem của mình
            return [IsAuthenticated()]
        else:
            # Other actions require authentication
            return [IsAuthenticated(), IsOwnerOrAdmin()]

    def get_queryset(self):
        """
        Override to filter histories based on user role
        - Admin can see all histories
        - Regular users can only see their own histories
        """
        queryset = super().get_queryset()

        # Nếu action là create, trả về queryset đầy đủ
        if self.action == 'create':
            return queryset

        # Lấy token từ request
        token = extract_token(self.request)
        if not token:
            return queryset.none()  # Trả về queryset rỗng nếu không có token

        try:
            # Validate token và lấy payload
            payload = validate_token(token)

            # Admin có thể xem tất cả lịch sử
            if payload.get('role') == 'admin':
                return queryset

            # User thường chỉ có thể xem lịch sử của mình
            user_id = payload.get('user_id')
            return queryset.filter(id_user__id=user_id)
        except:
            return queryset.none()  # Trả về queryset rỗng nếu token không hợp lệ

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Filter by user_id if provided
        user_id = request.query_params.get('user_id', None)
        if user_id:
            queryset = queryset.filter(id_user__id=user_id)

        # Apply date filtering if provided
        created_at__gte = request.query_params.get('created_at__gte', None)
        if created_at__gte:
            queryset = queryset.filter(created_at__gte=created_at__gte)

        # Apply search filter if provided
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(result__icontains=search)

        # Apply pagination
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            result = self.get_paginated_response(serializer.data)
            data = result.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data

        return create_response(
            data=data,
            message="Lấy danh sách lịch sử thành công",
            status_code=status.HTTP_200_OK
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return create_response(
            data=serializer.data,
            message=f"Lấy thông tin lịch sử ID {instance.id} thành công",
            status_code=status.HTTP_200_OK
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return create_response(
                data=serializer.data,
                message="Tạo lịch sử mới thành công",
                status_code=status.HTTP_201_CREATED
            )
        return create_response(
            message="Lỗi khi tạo lịch sử",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if serializer.is_valid():
            self.perform_update(serializer)
            return create_response(
                data=serializer.data,
                message=f"Cập nhật lịch sử ID {instance.id} thành công",
                status_code=status.HTTP_200_OK
            )
        return create_response(
            message="Lỗi khi cập nhật lịch sử",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        history_id = instance.id
        self.perform_destroy(instance)
        return create_response(
            message=f"Xóa lịch sử ID {history_id} thành công",
            status_code=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def by_user(self, request):
        """
        Lấy lịch sử theo user_id

        Query params:
        - user_id: ID của người dùng cần lấy lịch sử
        - search: Tìm kiếm trong kết quả
        - created_at__gte: Lọc theo thời gian tạo (từ ngày)
        - page: Số trang
        - page_size: Số lượng kết quả mỗi trang
        """
        # Lấy user_id từ query params
        user_id = request.query_params.get('user_id', None)

        if not user_id:
            return create_response(
                message="Thiếu tham số user_id",
                errors={"user_id": ["Tham số user_id là bắt buộc"]},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Kiểm tra quyền truy cập
        token = extract_token(request)
        if not token:
            return create_response(
                message="Không có quyền truy cập",
                errors={"detail": ["Authentication credentials were not provided"]},
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        try:
            payload = validate_token(token)

            # Nếu không phải admin và không phải chủ sở hữu, từ chối truy cập
            if payload.get('role') != 'admin' and str(payload.get('user_id')) != user_id:
                return create_response(
                    message="Không có quyền truy cập",
                    errors={"detail": ["You do not have permission to view histories of this user"]},
                    status_code=status.HTTP_403_FORBIDDEN
                )

            # Lấy user từ database
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return create_response(
                    message="Người dùng không tồn tại",
                    errors={"user_id": [f"Không tìm thấy người dùng với ID {user_id}"]},
                    status_code=status.HTTP_404_NOT_FOUND
                )

            # Lấy lịch sử của user
            queryset = History.objects.filter(id_user=user)

            # Apply date filtering if provided
            created_at__gte = request.query_params.get('created_at__gte', None)
            if created_at__gte:
                queryset = queryset.filter(created_at__gte=created_at__gte)

            # Apply search filter if provided
            search = request.query_params.get('search', None)
            if search:
                queryset = queryset.filter(result__icontains=search)

            # Apply ordering
            queryset = queryset.order_by('-created_at')  # Mới nhất lên đầu

            # Apply pagination
            page = self.paginate_queryset(queryset)

            if page is not None:
                serializer = self.get_serializer(page, many=True)
                result = self.get_paginated_response(serializer.data)
                data = result.data
            else:
                serializer = self.get_serializer(queryset, many=True)
                data = serializer.data

            return create_response(
                data=data,
                message=f"Lấy lịch sử của người dùng {user.username} thành công",
                status_code=status.HTTP_200_OK
            )

        except Exception as e:
            return create_response(
                message="Lỗi khi lấy lịch sử",
                errors={"detail": [str(e)]},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


def text_to_speech(request):
    """
    API endpoint để tạo file âm thanh từ văn bản

    Tham số:
    - text: Văn bản cần chuyển đổi thành âm thanh
    - language: Ngôn ngữ (mặc định: 'vi')
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Chỉ hỗ trợ phương thức POST'}, status=405)

    try:
        # Lấy dữ liệu từ request
        # Kiểm tra cả request.POST và request.body
        if request.POST:
            text = request.POST.get('text', '')
            language = request.POST.get('language', 'vi')
        elif request.body:
            try:
                data = json.loads(request.body)
                text = data.get('text', '')
                language = data.get('language', 'vi')
            except json.JSONDecodeError:
                # Ghi log lỗi
                print("Lỗi parse JSON từ request.body")
                # Trả về lỗi
                return JsonResponse({'status': 'error', 'message': 'Dữ liệu không hợp lệ'}, status=400)
        else:
            text = ''
            language = 'vi'

        if not text:
            return JsonResponse({'status': 'error', 'message': 'Thiếu tham số text'}, status=400)

        # Ghi log để debug
        print(f"Xử lý yêu cầu TTS: độ dài text={len(text)}, ngôn ngữ={language}")

        # Nếu văn bản ngắn, tạo file âm thanh trực tiếp
        if len(text) <= 200:
            tts = gTTS(text=text, lang=language, slow=False)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)

            # Trả về file âm thanh
            response = HttpResponse(fp.read(), content_type='audio/mpeg')
            response['Content-Disposition'] = f'attachment; filename="audio_{language}.mp3"'
            return response

        # Nếu văn bản dài, chia thành nhiều đoạn và ghép lại
        chunks = split_text_into_chunks(text, 200)
        print(f"Đã chia văn bản thành {len(chunks)} đoạn")

        # Tạo thư mục tạm để lưu các file âm thanh
        temp_dir = tempfile.mkdtemp()
        temp_files = []

        try:
            # Tạo file âm thanh cho từng đoạn
            for i, chunk in enumerate(chunks):
                temp_file = os.path.join(temp_dir, f'chunk_{i}.mp3')
                tts = gTTS(text=chunk, lang=language, slow=False)
                tts.save(temp_file)
                temp_files.append(temp_file)
                print(f"Đã tạo đoạn {i+1}/{len(chunks)}")

            # Ghép các file âm thanh lại với nhau
            combined = AudioSegment.empty()
            for temp_file in temp_files:
                audio_segment = AudioSegment.from_mp3(temp_file)
                combined += audio_segment

            # Lưu file âm thanh đã ghép vào buffer
            output = io.BytesIO()
            combined.export(output, format='mp3')
            output.seek(0)
            print("Đã ghép các đoạn âm thanh thành công")

            # Trả về file âm thanh đã ghép
            response = HttpResponse(output.read(), content_type='audio/mpeg')
            response['Content-Disposition'] = f'attachment; filename="audio_{language}.mp3"'
            return response

        finally:
            # Xóa các file tạm
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)

    except Exception as e:
        # Ghi log chi tiết lỗi
        error_details = traceback.format_exc()
        print(f"Lỗi text-to-speech: {error_details}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def split_text_into_chunks(text, max_length):
    """
    Chia văn bản thành các đoạn nhỏ, cố gắng cắt ở dấu câu hoặc khoảng trắng
    """
    chunks = []
    start = 0

    while start < len(text):
        # Nếu phần còn lại của văn bản ngắn hơn max_length, lấy toàn bộ
        if start + max_length >= len(text):
            chunks.append(text[start:])
            break

        # Tìm vị trí cắt phù hợp (dấu câu hoặc khoảng trắng)
        end = start + max_length
        cut_position = end

        # Ưu tiên cắt ở dấu câu
        punctuation_marks = [".", "!", "?", ";", ":", ","]
        for i in range(end, start, -1):
            if i < len(text) and text[i] in punctuation_marks:
                cut_position = i + 1  # Bao gồm cả dấu câu
                break

        # Nếu không tìm thấy dấu câu, cắt ở khoảng trắng
        if cut_position == end:
            for i in range(end, start, -1):
                if i < len(text) and text[i] == " ":
                    cut_position = i + 1  # Bao gồm cả khoảng trắng
                    break

        # Nếu không tìm thấy vị trí cắt phù hợp, cắt ở max_length
        if cut_position == end and start != 0:
            cut_position = end

        chunks.append(text[start:cut_position])
        start = cut_position

    return chunks
