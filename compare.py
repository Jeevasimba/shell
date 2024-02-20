import ast
from functools import wraps
import os
from zipfile import ZipFile
import zipfile
import threading
import tempfile
import os
import shutil
import zipfile
from django.http import HttpResponse
from django.views import View
from django.conf import settings
import numpy as np
import cv2
from io import BytesIO, StringIO
from django.middleware.csrf import get_token
from django.db.models import *
from django.core.files import File
from django.core.files.base import ContentFile
import tempfile
from django.shortcuts import get_object_or_404, redirect, render
import csv
from django.db import transaction
import pandas as pd
import json
from django.http import HttpResponseRedirect, JsonResponse
from shell import settings
from .models import *
from shell.settings import MEDIA_ROOT
from django.utils import timezone
from .forms import MyModelForm
from django.http import HttpResponse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render
from .models import upcdata
from django.db.models.functions import *
from .upload_excel_upc import upload_excel_upc
import threading
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font

def loginrequired(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        try:
            session = request.session
            if 'empId' in session and 'permlist' in session: #and 'location' in session
                EmpID = request.session.get('empId')
                try:
                    # permlist = Roles.objects.filter(userprofile_id=EmpID,preference='role').values('role')
                    # request.session['permlist'] = [i['role'] for i in permlist]

                    deprtmntlist = Roles.objects.filter(userprofile__userstatus= 'active',userprofile_id=EmpID,preference='specialisation').values('role')
                    request.session['userdept'] = [i['role'] for i in deprtmntlist if i['role'].strip()]
                except Exception as er:
                    print(er)
                return view_func(request, *args, **kwargs)
            else:
                print('not in')
                request.session.flush()
                request.session.clear()
                return redirect('/')
        except Exception as er:
            print(er)
            return redirect('/')
    return _wrapped_view

@loginrequired
def upc_finder(request):
    return render(request, 'upc_finder/upc_finder.html')

@loginrequired
def get_suggestions(request):
    if request.method == 'POST':
        input_value = request.POST.get('input', '')
        suggestions = list(upcdata.objects.filter(name__icontains=input_value).values('name'))
        return JsonResponse({'suggestions': suggestions})

@loginrequired
def get_answer(request):
    if request.method == 'POST':
        product_name = request.POST.get('productName', '')
        try:
            answer = upcdata.objects.get(name=product_name).upc
        except upcdata.DoesNotExist:
            answer = 'Product not found'
        return JsonResponse({'answer': answer})


@loginrequired
def get_product_data(request):
    products = upcdata.objects.all()
    data = [{'name': product.name, 'upc': product.upc} for product in products]
    return JsonResponse(data, safe=False)

def loginView(request):
    if request.method == 'POST':
        employeeid = request.POST.get('empid')
        # employeename = request.POST.get('empname')
        password = request.POST.get('password')

        if password == 'admin123$':

            UserID, created = userProfile.objects.update_or_create(
                employeeID=employeeid)
            request.session['empId'] = UserID.id
            request.session['employeeID'] = employeeid
           
            # Roles.objects.update_or_create(
            #   userprofile_id=UserID.id, role='Super Admin',preference='role')
            
            permlist = Roles.objects.filter(userprofile__userstatus= 'active',userprofile_id=UserID.id,preference='role').values('role')
            request.session['permlist'] = [i['role'] for i in permlist if i['role'].strip()]

            deprtmntlist = Roles.objects.filter(userprofile_id=UserID.id,preference='specialisation').values('role')
            request.session['userdept'] = [i['role'] for i in deprtmntlist if i['role'].strip()]
            if permlist:
                return render(request, 'index.html')
            else:
                request.session.flush()
                request.session.clear()
                return render(request, 'pages/registration/login.html')
        else:
            request.session.flush()
            request.session.clear()
            return render(request, 'pages/registration/login.html')
    else:  
        if request.session.get('permlist'):
            return render(request, 'index.html')
        else:
            request.session.flush()
            request.session.clear()
            return render(request, 'pages/registration/login.html')
    
@loginrequired
def logoutView(request):
    request.session.flush()
    request.session.clear()
    request.session.clear_expired()
    return redirect('/')

@loginrequired
def upc(request):
    return render(request, 'UPC.html')

@loginrequired
def home(request):
    return render(request, 'index.html')


@loginrequired
def userTable(request):
    if request.method == "POST":
        # print("in")
        employeeID = request.POST.get('employeeID')
        # print(employeeID,"employeeID")
        userdatas = userProfile.objects.filter(employeeID=employeeID).values(
            'id', 'employeeName', 'employeeID', 'created_at')
        roles = Roles.objects.filter(
            userprofile_id__employeeID=employeeID).values('role')
        preference_type = Trackerfile_data.objects.values("planogram_type").distinct()
        return render(request, 'pages/userManagement.html', {'userdatas': userdatas[0], 'roles': [i['role'] for i in roles],'preference_type':preference_type})
    else:
        preference_type = Trackerfile_data.objects.values("planogram_type").distinct()
        userdatas = userProfile.objects.values(
            'id', 'employeeName', 'employeeID', 'created_at')
        roles = Roles.objects.values('userprofile_id__employeeID','role','preference')
        return render(request, 'pages/UserTable.html', {'userDatas': userdatas,'roles':roles,'preference_type':preference_type})
    
@loginrequired
def OverAllRole(request):
    EmpID = request.session.get('empId')
    if request.method == 'POST':
        employeeID = request.POST.get('employeeid')
        roles = request.POST.getlist('roles')
        try:
            # user = userProfile.objects.create(employeeID=employeeID)
            # user.set_password('admin')
            # user.save()
            UseTable = userProfile.objects
            empall = [eid.strip() for eid in employeeID.split(',')]
            for EmpId in empall:
                UseTable.update_or_create(
                    employeeID=EmpId,userstatus='active')

            UserID = UseTable.filter(
                employeeID__in=empall).values('id').first()
            for role in roles:
                Roles.objects.create(preference = 'role',
                    userprofile_id=UserID['id'], role=role, created_by_id=EmpID)
            return redirect('/app/userTable/')

        except Exception as er:
            return JsonResponse({'status': 400, 'message': str(er)})
    else:
        # print("out")
        return redirect('/app/userTable/')

@loginrequired
def UserManagement(request):
    EmpID = request.session.get('empId')
    if request.method == "POST":
        key = request.POST.get('key')
        # if key == 'userdata':
        employeeID = request.POST.get('employeeid')
        employeeName = request.POST.get('employeeName')
                
        roles = request.POST.get('role')
        prefns = request.POST.get('preference')

        user_profile, created = userProfile.objects.update_or_create(
            employeeID=employeeID,
            defaults={'employeeName': employeeName}
        )

        try:
            Roles.objects.filter(preference = 'role').update_or_create(
                userprofile_id=user_profile.id,
                defaults={
                    'role':roles,
                    'created_by_id':EmpID
                }
            )

            Roles.objects.filter(preference = 'specialisation').update_or_create(
                userprofile_id=user_profile.id,
                defaults= {
                    'role': prefns,
                    'preference':'specialisation',
                    'created_by_id':EmpID}
            )

        except Exception as er:
            return JsonResponse({'status': 400, 'message': str(er)})
        return redirect('/app/userTable/')
    else:
        preference_type = Trackerfile_data.objects.values("planogram_type").distinct()
        return render(request, 'pages/userManagement.html',{'preference_type':preference_type})


@loginrequired
def FileUpload(request):
    if request.method == "POST":
        EmpID = request.session.get('empId')
        key = request.POST.get('key')
        slctcycle = request.POST.get('cycle')

        trackerFile = request.FILES.get('trackerfile',None)
        if trackerFile:
            excel_data = pd.read_csv(trackerFile)
            to_dict = excel_data.to_dict('records')

        planogramPDF_File = request.FILES.get('planogram_pdf',None)
        if planogramPDF_File:
            pdf_zip_ref = ZipFile(planogramPDF_File, 'r')
            pdf_file_infos = pdf_zip_ref.infolist()

        storeImgs = request.FILES.get('planogram_image',None)
        if storeImgs:
            imgs_zip_ref = ZipFile(storeImgs, 'r')
            imgs_file_infos = imgs_zip_ref.infolist()

        last_RECD = BaseFile.objects.order_by('-id').first()
        if last_RECD:
            last_id = int(last_RECD.cycle[5:])
            if slctcycle == 'new':
                new_id = last_id + 1
            else:
                new_id = last_id
                baseid = last_RECD.id
        else:
            new_id = 1
        cycle = f'CYCLE{new_id:05}'
        cyclename = 'Upload/' + cycle + '/'
        if slctcycle == 'new':
            baseid = BaseFile.objects.create(cycle = cycle,created_by_id=EmpID,filename=trackerFile)
            baseid = baseid.id
        try:
            with transaction.atomic():
                if slctcycle == 'new' or len(to_dict) > 0:
                    for i in to_dict:
                        Trackerfile_data.objects.create(
                            baseid_id = baseid,
                            store_number = i.get('Store Number',None),
                            four_digit_store_number = i.get('4 - Digit Store Number',None),
                            store_name = i.get('Store Name',None),
                            department_name = i.get('Department Name',None),
                            planogram_type = i.get('Planogram Type',None),
                            planogram_name = i.get('Planogram Name',None),
                            no_of_skus = i.get('No. of SKUs',None),
                            created_by_id = EmpID
                        )
                if planogramPDF_File:
                    for PdfFIle in pdf_file_infos:
                        pdf_filename = PdfFIle.filename
                        pdf_FileNames = pdf_filename.split("/")[-1]
                        movedPDFfilename = cyclename + 'PlanogramPDF/' + \
                                str(pdf_FileNames)
                        if pdf_filename.endswith('.pdf'):
                            pdf_file = pdf_zip_ref.read(pdf_filename)
                            PlanogramePDF.objects.create(baseid_id = baseid,created_by_id = EmpID,
                                planograme_pdf=ContentFile(pdf_file, name=movedPDFfilename)
                            )
                if storeImgs:
                    for img_file_info in imgs_file_infos:
                        img_filename = img_file_info.filename   
                        # img_FileNames = img_filename.split("/")[-1]
                        # foldername = img_filename.split("/")[1]
                        base_path = img_filename.split("/")[0]
                        moved_img_filename = f"{cyclename}{'Store-Images/'}{img_filename[len(base_path):]}"
                        if img_filename.endswith('.jpg'): # and str(i['Planogram Type']) in foldername and str(i['4 - Digit Store Number']) in img_FileNames:
                            img_file =  imgs_zip_ref.read(img_filename)
                            storeImages.objects.create(baseid_id = baseid,created_by_id = EmpID,
                                store_images=ContentFile(img_file, name=moved_img_filename)
                            )

                    t1 = threading.Thread(target=print_square, args=(cycle,))
                    t1.start()
                    comparestatus.objects.update_or_create(cycle=cycle, defaults={'status': False})
                responseData = {'status': 'success',
                                'message': 'Data Upload Successfully'}
                return JsonResponse(responseData)
        except Exception as er:
            print(er)
            responseData = {'status': 'failed',
                            'result': ",File Already Exist"}
            return JsonResponse(responseData)
    else:
        last_RECD = BaseFile.objects.order_by('-id').first()
        if last_RECD:
            lastcycle = last_RECD.cycle
            trackerfile_data = Trackerfile_data.objects.values('baseid_id',track_uploaded = F('created_by__employeeID'),cycle=F('baseid__cycle')).annotate(tracker_count=Count('baseid'),trkuploaded_at=Max('created_at__date')).distinct()
            planograme_data = PlanogramePDF.objects.values('baseid_id',plang_uploaded = F('created_by__employeeID')).annotate(planograme_count=Count('baseid'),plnuploaded_at=Max('created_at__date')).distinct()
            storeimage_data = storeImages.objects.values('baseid_id',storeimg_uploaded = F('created_by__employeeID')).annotate(storeimage_count=Count('baseid'),struploaded_at=Max('created_at__date')).distinct()

            tracker_df = pd.DataFrame(trackerfile_data)
            planograme_df = pd.DataFrame(planograme_data)
            storage_df = pd.DataFrame(storeimage_data)
            if not tracker_df.empty and not planograme_df.empty:
                mrgd = pd.merge(tracker_df,planograme_df,on='baseid_id',how='outer')
                if not storage_df.empty:
                    mrgd = pd.merge(mrgd,storage_df,on='baseid_id',how='outer')
                    datas = mrgd.to_dict('records')
                    return render(request, 'pages/upload.html',{'cycle':lastcycle,'datas':datas})   
            else:
                datas = []
        else:
            datas = []
            lastcycle = []
        return render(request, 'pages/upload.html',{'cycle':lastcycle,'datas':datas})   
         
@loginrequired
def tracker_production(request):   
    EmpID = request.session.get('empId') 
    department = request.session.get('userdept') 
    if request.method == 'POST':
        trackerid = request.POST.get('trackerid')
        idval = request.POST.get('idval')
        no_of_missing_skus = request.POST.get('no_of_missing_skus',None)
        incorrectly_placed_skus = request.POST.get('incorrectly_placed_skus',None)
        workable_non_workable = request.POST.get('workable_non_workable',None)
        Image_Qualified_for_Compliance = request.POST.get('Image_Qualified_for_Compliance',None)
        No_of_Bays = request.POST.get('No_of_Bays',None)
        No_of_Shelves = request.POST.get('No_of_Shelves',None)
        Size_of_Bays = request.POST.get('Size_of_Bays',None)
        Status = request.POST.get('Status',None)
        Remarks = request.POST.get('Remarks',None)
        Prod_pdf = request.FILES.get('production_pdf',None)
        
        one = get_object_or_404(Production, trackerid_id=idval)
        one.production_pdf = Prod_pdf
        one.save()

        Production.objects.filter(trackerid_id = idval).update(no_of_missing_skus = no_of_missing_skus,
                                            incorrectly_placed_skus = incorrectly_placed_skus,
                                            workable_non_workable = workable_non_workable,
                                            Image_Qualified_for_Compliance = Image_Qualified_for_Compliance,
                                            No_of_Bays = No_of_Bays,
                                            No_of_Shelves = No_of_Shelves,
                                            Size_of_Bays = Size_of_Bays,
                                            Status = 'completed',
                                            
                                            Remarks = Remarks, end_time=timezone.now())
        
        Trackerfile_data.objects.filter(id = idval).update(production_status = "completed")
        return HttpResponseRedirect('/app/tracker_production/')        
    else:
        with transaction.atomic():
            query = Q()
            if len(department) != 0:
                query = Q(planogram_type__in = department)
            instance = Trackerfile_data.objects.select_for_update(skip_locked=True).filter(query &
                            ((Q(production_status ='picked') & Q(prod_empid =EmpID)) | Q(production_status ='not_picked'))).values('id','baseid','store_number','four_digit_store_number','department_name', 'planogram_type','planogram_name','no_of_skus').order_by('-production_status','store_number').first()
            if instance:
                if Production.objects.filter(trackerid_id=instance['id']).exists():
                    Production.objects.filter(trackerid_id=instance['id']).update(start_time = timezone.now())
                else:
                    prodid = Production.objects.create(trackerid_id=instance['id'], start_time = timezone.now(),created_by_id = EmpID)
                    Trackerfile_data.objects.filter(id=instance['id']).update(production_status='picked', prodid_id=prodid.id,prod_empid=EmpID)
                
                planogrampdf = PlanogramePDF.objects.filter(baseid_id = instance['baseid'], planograme_pdf__contains=str(instance['planogram_name']).replace(' ', '_')).values('planograme_pdf')
                storeimg = storeImages.objects.filter(Q(baseid_id = instance['baseid']) & Q(store_images__contains=instance['four_digit_store_number']) &
                                                Q(store_images__contains=instance['planogram_type'])).values('store_images')
            else:
                instance = []
                planogrampdf = []
                storeimg = []
        return render(request, 'pages/tracker_production.html',{'trackingdata':instance,'planogrampdf':planogrampdf,'storeimg':storeimg})




def compare_images_opencv(zip_image_content, existing_image_path):
    
    existing_image = cv2.imread(existing_image_path)
    
    if existing_image is None:
        return False  

    try:
        
        zip_image = cv2.imdecode(np.frombuffer(zip_image_content, np.uint8), -1)
    except cv2.error as e:
        print(f"Error decoding image: {e}")
        return False

   
    if zip_image is not None and zip_image.size != 0:
        
        if existing_image.shape == zip_image.shape:
            difference = cv2.subtract(existing_image, zip_image)
            b, g, r = cv2.split(difference)
            if cv2.countNonZero(b) == 0 and cv2.countNonZero(g) == 0 and cv2.countNonZero(r) == 0:
                return True  

    return False

@loginrequired
def process_selected_duplicates(request):
    if request.method == 'POST':
        selected_images = request.POST.getlist('selected_images[]')
        print("Selected Images:", selected_images)
        return JsonResponse({'status': selected_images})

    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})



# def get_unchecked_folders_paths():
#     unchecked_folders = imagecompfolders.objects.filter(checked='false')

#     unchecked_folder_paths = []

#     for folder in unchecked_folders:
#         folder_path = os.path.join(MEDIA_ROOT+'\\upload\\', folder.folders)
#         unchecked_folder_paths.append(folder_path)

#     return unchecked_folder_paths

# unchecked_folders_paths = get_unchecked_folders_paths()
# for folder_path in unchecked_folders_paths:
#     print(folder_path)


# 
# def add_upc(request):
#     if request.method == 'POST':
#         form = MyModelForm(request.POST, request.FILES)

        
#         if form.is_valid():
            
#             main_instance = form.save()

            
#             for key, value in request.POST.items():
#                 if key.startswith('name_'):
#                     field_num = key.split('_')[1]
#                     name = value
#                     upc = request.POST.get(f'upc_{field_num}')
#                     image = request.FILES.get(f'image_{field_num}')

                    
#                     if upc and image:
                        
#                         filename, file_extension = os.path.splitext(image.name)
#                         unique_filename = f"{name}_{timezone.now().strftime('%Y%m%d%H%M%S')}_{get_random_string(5)}{file_extension}"

                        
#                         target_directory = os.path.join(settings.BASE_DIR, 'media', 'images')

                        
#                         os.makedirs(target_directory, exist_ok=True)

                        
#                         with open(os.path.join(target_directory, unique_filename), 'wb') as destination:
#                             for chunk in image.chunks():
#                                 destination.write(chunk)

#                         instance = upcdata(name=name, upc=upc, image=unique_filename)
#                         instance.save()

#             messages.success(request, 'Form submitted successfully.')

            
#             return redirect('upload_view')

#     else:
#         form = MyModelForm()

#     return render(request, 'upc_upload.html', {'form': form})

def add_upc(request):
    if request.method == 'POST':
        form = MyModelForm(request.POST)

        if form.is_valid():
            main_instance = form.save(commit=False)
            main_instance.save()

            # Process additional fields
            for key, value in request.POST.items():
                if key.startswith('name_'):
                    field_num = key.split('_')[1]
                    name = value
                    upc = request.POST.get(f'upc_{field_num}')

                    if upc:
                        instance = upcdata(name=name, upc=upc)
                        instance.save()

            messages.success(request, 'Form submitted successfully.')
            return redirect('upload_view')

    else:
        form = MyModelForm()

    return render(request, 'upload_page.html', {'form': form})


def compare_folder_images(folder_path, media_root , selected_folder):
    print("folder path : ",folder_path, "media folder : ",media_root ,"current cycle : ", selected_folder)
    duplicate_images = None

    folder_data = load_folder_images(folder_path)
    duplicate_images = find_duplicate_images(folder_data, media_root,folder_path,selected_folder)
    
    comparestatus.objects.filter(cycle=selected_folder).update(status=True)
    return duplicate_images

def load_folder_images(folder_path):
    print('loading ############################################################################################')
    folder_data = {}

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            path = os.path.join(root, file)
            with open(path, 'rb') as file:
                folder_data[path] = file.read()

    return folder_data

def find_duplicate_images(folder_data, directory,folder_path,selected_folder):
    print('finding now##################################################################################################################')

    for root, dirs, files in os.walk(directory):
        for file in files:
            path = os.path.join(root, file)

            for folder_filename, folder_file_content in folder_data.items():

                relative_original = os.path.relpath(folder_filename, os.path.join(MEDIA_ROOT, 'Upload'))
                relative_duplicate = os.path.relpath(path, os.path.join(MEDIA_ROOT, 'Upload'))

		# getting the path    and split path
		split_relative_original = relative_original.split("/")
		split_relative_duplicate = relative_duplicate.split("/")

		#   original and duplicate path
		result_relative_original = "/".join(split_relative_original[1:])
		result_relative_duplicate = "/".join(split_relative_duplicate[1:])
		
		# file name
		filename_original = split_relative_original[-1]
		filename_duplicate = split_relative_duplicate[-1]
		
		# compare the shop name
		first_four_digits_original = filename_original.split('_')[0]
		first_four_digits_duplicate = filename_duplicate.split('_')[0]
		
		if relative_original!=relative_duplicate and (result_relative_original==result_relative_duplicate  and first_four_digits_original == first_four_digits_duplicate ):
		    print("relative_original =", result_relative_original)
                    print("relative_duplicate =", result_relative_duplicate)
                    if compare_images_opencv(folder_file_content, path):
                        

                        
                        if not is_hierarchy_folder(folder_path, path):
                            
                                existing_entry = dupicatedata.objects.filter(
                                    original=relative_original,
                                    duplicate=relative_duplicate,
                                    cyclename=selected_folder
                                ).first()

                                if existing_entry is None and relative_original!=relative_duplicate:
                                    
                                    dupicatedata.objects.create(
                                        original=relative_original,
                                        duplicate=relative_duplicate,
                                        cyclename=selected_folder
                                    )
                                
    return 'result'

def compare_images_opencv(folder_image_content, existing_image_path):
    print('comparing now #############################################################################################################################################################')
    existing_image = cv2.imread(existing_image_path)

    if existing_image is None:
        return False  

    try:
        folder_image = cv2.imdecode(np.frombuffer(folder_image_content, np.uint8), -1)
    except cv2.error as e:
        print(f"Error decoding image: {e}")
        return False

    if folder_image is not None and folder_image.size != 0:
        if existing_image.shape == folder_image.shape:
            difference = cv2.subtract(existing_image, folder_image)
            b, g, r = cv2.split(difference)
            if cv2.countNonZero(b) == 0 and cv2.countNonZero(g) == 0 and cv2.countNonZero(r) == 0:
                return True  

    return False

def cycle(request, path):
    folder_path = os.path.abspath(MEDIA_ROOT+'/'+path)
    folders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
    
    return JsonResponse({'folders': folders})

def url_to_link(url):
    if url:
        # url = url.replace('..','')
        # return f'<a href=http://localhost:8000/media/Upload/"{url}">http://localhost:8000/media/Upload/{url}</a>'  
        return   f'http://g26.local:8000/media/Upload/{url}'
    else:
        return ''

    
def comp(request):
    if request.method == 'POST':
        selected_folder = request.POST.get('selected_folder')
        # imglist = compare_folder_images(MEDIA_ROOT+'\\upload\\'+selected_folder,MEDIA_ROOT,selected_folder)
        # duplicate_data = dupicatedata.objects.all()
        duplicate_data = dupicatedata.objects.filter(cyclename=selected_folder).values()
        
        return render(request, 'pages/comp.html',{'imglist': duplicate_data})

    return render(request, 'pages/comp.html')

def is_hierarchy_folder(parent_path, child_path):
    
    if parent_path == child_path:
        return True
    
    abs_parent_path = os.path.abspath(parent_path)
    abs_child_path = os.path.abspath(child_path)

    
    return abs_child_path.startswith(abs_parent_path + os.path.sep)


@loginrequired
def production_report(request):
    production_report_data = Production.objects.filter(trackerid_id__production_status="completed").values('id','trackerid_id__store_number','trackerid_id__department_name','trackerid_id__planogram_type','trackerid_id__planogram_name',"no_of_missing_skus",
                            "incorrectly_placed_skus",
                            "workable_non_workable",
                            "Image_Qualified_for_Compliance",
                            "No_of_Bays",
                            "No_of_Shelves",
                            "Size_of_Bays",
                            "Status",
                            "Remarks",
                            "start_time",
                            "end_time",
                            "created_by_id__employeeID")
    return render(request,'pages/production_report.html',{'production_report_data':production_report_data})



@loginrequired
def TrackerFile_Audit(request):
    EmpID = request.session.get('empId') 
    department = request.session.get('userdept')
    if request.method == 'POST':
        trackerid = request.POST.get('trackerid')
        idval = request.POST.get('idval')
        no_of_missing_skus = request.POST.get('no_of_missing_skus',None)
        incorrectly_placed_skus = request.POST.get('incorrectly_placed_skus',None)
        workable_non_workable = request.POST.get('workable_non_workable',None)
        Image_Qualified_for_Compliance = request.POST.get('Image_Qualified_for_Compliance',None)
        No_of_Bays = request.POST.get('No_of_Bays',None)
        No_of_Shelves = request.POST.get('No_of_Shelves',None)
        Size_of_Bays = request.POST.get('Size_of_Bays',None)
        Remarks = request.POST.get('Remarks',None)
        audt_pdf = request.FILES.get('audit_pdf',None)
        
        one = get_object_or_404(Audit, trackerid_id=idval)
        one.audit_pdf = audt_pdf
        one.save()

        Audit.objects.filter(trackerid_id = idval).update(no_of_missing_skus = no_of_missing_skus,
                                            incorrectly_placed_skus = incorrectly_placed_skus,
                                            workable_non_workable = workable_non_workable,
                                            Image_Qualified_for_Compliance = Image_Qualified_for_Compliance,
                                            No_of_Bays = No_of_Bays,
                                            No_of_Shelves = No_of_Shelves,
                                            Size_of_Bays = Size_of_Bays,
                                            Status = 'completed',
                                            
                                            Remarks = Remarks, end_time=timezone.now())
        
        Trackerfile_data.objects.filter(id = idval).update(audit_status = "completed")
        return HttpResponseRedirect('/app/tracker_audit/')      
    else:
        with transaction.atomic():
            query = Q(prodid__Status = 'completed')
            if len(department) != 0:
                query &= Q(planogram_type__in = department)
            instance = Trackerfile_data.objects.select_for_update(skip_locked=True).filter(query &
                            ((Q(audit_status ='picked') & Q(audit_empid =EmpID)) | Q(audit_status ='not_picked'))).values('id','baseid','store_number','four_digit_store_number','department_name',
                                'planogram_type','planogram_name','no_of_skus',
                                'prodid__no_of_missing_skus',
                                'prodid__incorrectly_placed_skus',
                                'prodid__workable_non_workable',
                                'prodid__Image_Qualified_for_Compliance',
                                'prodid__No_of_Bays',
                                'prodid__No_of_Shelves',
                                'prodid__Size_of_Bays',
                                'prodid__Remarks').order_by('-audit_status','store_number').first()
            if instance:
                if Audit.objects.filter(trackerid_id=instance['id']).exists():
                    Audit.objects.filter(trackerid_id=instance['id']).update(start_time = timezone.now())
                else:
                    audit = Audit.objects.create(trackerid_id=instance['id'], start_time = timezone.now(),created_by_id = EmpID)
                    Trackerfile_data.objects.filter(id=instance['id']).update(audit_status='picked', auditid=audit.id,audit_empid=EmpID)

                planogrampdf = PlanogramePDF.objects.filter(baseid_id = instance['baseid'],planograme_pdf__contains=str(instance['planogram_name']).replace(' ','_')).values('planograme_pdf')#.first()
                storeimg = storeImages.objects.filter(Q(baseid_id = instance['baseid']) & Q(store_images__contains=instance['four_digit_store_number']) &
                                                Q(store_images__contains=instance['planogram_type'])).values('store_images')
            else:
                instance = []
                planogrampdf = None
                storeimg = []
            return render(request, 'pages/tracker_audit.html',{'trackingdata':instance,'planogrampdf':planogrampdf,'storeimg':storeimg})



def print_square(selected_folder):
	compare_folder_images(MEDIA_ROOT+'/Upload/'+selected_folder,MEDIA_ROOT,selected_folder)


@loginrequired
def handle_todo_list(request):
    emp_id = request.session.get('empId') 
    if request.method == 'POST':
        task_data = request.POST.get('tasks')
        tracker_id = request.POST.get('trackerid')

        if task_data is not None:
            tasks = json.loads(task_data)

            # Get all existing Missing_upccode objects for the given tracker ID
            existing_upc_objs = Missing_upccode.objects.filter(missingtrackerid_id=tracker_id)

            # List to store UPCs to be removed
            upcs_to_remove = []

            for upc in existing_upc_objs:
                # If the UPC is not in the received tasks, add it to the list of UPCs to remove
                if upc.upcid.upc not in tasks:
                    upcs_to_remove.append(upc.upcid.upc)

            # Remove Missing_upccode objects corresponding to the UPCs to remove
            Missing_upccode.objects.filter(missingtrackerid_id=tracker_id, upcid__upc__in=upcs_to_remove).delete()

            # Create or update Missing_upccode objects for the received tasks
            for upc in tasks:
                upc_obj = upcdata.objects.filter(upc=upc).first()
                if upc_obj:
                    Missing_upccode.objects.update_or_create(
                        missingtrackerid_id=tracker_id,
                        upcid=upc_obj,
                        created_by_id=emp_id
                    )

            return JsonResponse({'message': 'Tasks received and processed successfully'}, status=200)
        else:
            return JsonResponse({'error': 'No tasks received'}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)
@loginrequired
def fileMamagement(request):
    if request.method == 'POST':        
        buttonValue = request.POST.get('buttonValue')
        employeeID = request.POST.get('employeeID')
        if buttonValue == 'Active': 
            userProfile.objects.filter( employeeID=employeeID).update(userstatus='active')           

        elif buttonValue == 'Inactive':
            userProfile.objects.filter( employeeID=employeeID).update(userstatus='inactive')    
            
        return JsonResponse({'status': 'Success'})
    
@loginrequired
def getUserStatus(request):
    if request.method == 'GET':
        employee_id = request.GET.get('employee_id')
        user = userProfile.objects.filter(employeeID=employee_id).first()
        if user:
            return JsonResponse({'user_status': user.userstatus})
        else:
            return JsonResponse({'error': 'User not found'}, status=404)
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
@loginrequired
def upload_upc_excel(request):
    if request.method == 'POST':
        form = upload_excel_upc(request.POST, request.FILES)
        if form.is_valid():
            
            df = pd.read_excel(request.FILES['file'])
            for index, row in df.iterrows():
                
                name_data = row['name']
                upc_data = row['upc']
                
                upcdata.objects.create(name=name_data, upc=upc_data)
            return render(request, 'excel_success.html')
    else:
        form = upload_excel_upc()
    return render(request, 'excel_upc.html', {'form': form})    

def missingupc_report(request):
    if request.method == 'POST':
        missingupc_cycle = request.POST.get('missingupc_cycle')

        missing_upc = Missing_upccode.objects.filter(missingtrackerid__baseid__cycle=missingupc_cycle)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="missing_upc_report.csv"'

        writer = csv.writer(response)
        writer.writerow(['Cycle', 'UPC','Four digit store number','Planogram name','Production by'])
        for record in missing_upc:
            writer.writerow([record.missingtrackerid.baseid.cycle, record.upcid.upc, record.missingtrackerid.four_digit_store_number, record.missingtrackerid.planogram_name, record.missingtrackerid.prodid.created_by.employeeID])
        return response
    else:
        cycles = Trackerfile_data.objects.values(cycle=F('baseid__cycle')).distinct()
        return render(request, 'pages/missing_upc_report.html', {'cycles': cycles})
    
@loginrequired
def resetproduction(request):
    cycles = Trackerfile_data.objects.filter().values('baseid__cycle').exclude(production_status='completed').exclude(audit_status='completed').order_by('-baseid__cycle').distinct()
    if request.method == 'POST':
        key = request.POST.get('key')
        if key == 'getdata':
            resetfor = request.POST.get('resetfor')
            sltcycle = request.POST.get('cycle')
            if resetfor and sltcycle:
                if resetfor == 'Production':
                    query = Q(production_status='picked')
                elif resetfor == 'Audit':
                    query = Q(audit_status='picked')
                production_status = Trackerfile_data.objects.filter(query,baseid__cycle= sltcycle).values('id','store_number','four_digit_store_number','store_name','department_name','planogram_type','planogram_name','prodid_id__created_by__employeeID',cycle = F('baseid__cycle'))
            else:
                production_status = []
            return render(request, 'pages/reset_asign_user.html', {'resetfor': resetfor,'cycles':cycles,'production_status': production_status})
        elif key == 'putdata':
            resetfor = request.POST.get('resetfor')
            checked_data = request.POST.getlist('checkedids[]')
            if resetfor == 'Production':
                Trackerfile_data.objects.filter(id__in = checked_data).update(prod_empid_id=None,production_status='not_picked')
            elif resetfor == 'Audit':
                Trackerfile_data.objects.filter(id__in = checked_data).update(audit_empid_id=None,audit_status='not_picked')
            return JsonResponse({'status':200,'message':'success'})
    else:
        return render(request, 'pages/reset_asign_user.html', {'cycles':cycles,'production_status': []})

def comparision_status(request):
    data = list(comparestatus.objects.filter(status=False).values())
    return JsonResponse({'data': data})

def download_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="data.csv"'

    writer = csv.writer(response)
    writer.writerow(['name', 'upc'])

    upc_data = upcdata.objects.all()
    for data in upc_data:
        writer.writerow([data.name, data.upc])

    return response

@loginrequired
def projectsettings(request):
    return render(request,'pages/projectsettings.html')


def create_zip_file(zip_path, file_data, cyclenamefilter):
    with zipfile.ZipFile(zip_path, 'w') as zip_file:
        for original, duplicate, cyclename in file_data:
            if cyclename == cyclenamefilter:
                # Assume 'media/Upload' is the folder where your files are stored
                original_path = os.path.join(settings.MEDIA_ROOT, 'Upload', original)
                duplicate_path = os.path.join(settings.MEDIA_ROOT, 'Upload', duplicate)

                # Add the duplicate files to the zip with the desired folder structure
                zip_file.write(duplicate_path, os.path.join(cyclename, duplicate))


class ZipDownloadView(View):
    def get(self, request, cyclename):
        # Replace with the actual query to fetch duplicate data from the database
        duplicate_file_data = dupicatedata.objects.values_list('original', 'duplicate', 'cyclename').filter(duplicate__isnull=False)
        print(cyclename)
        # Create a temporary directory and file
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, 'file.zip')

            # Create the zip file
            create_zip_file(zip_path, duplicate_file_data, cyclename)

            # Open the zip file and serve it as an HTTP response
            with open(zip_path, 'rb') as zip_file:
                response = HttpResponse(zip_file.read(), content_type='application/zip')
                response['Content-Disposition'] = 'attachment; filename="duplicate_files.zip"'

        return response
    

class XLDownloadView(View):
    def get(self, request, cyclename):    
        selected_folder = cyclename
        duplicate_data = dupicatedata.objects.filter(cyclename=selected_folder).values()

        unique_originals = dupicatedata.objects.filter(cyclename=selected_folder).values_list('original', flat=True).distinct()

        folder_path = os.path.abspath(os.path.join(MEDIA_ROOT, 'Upload'))
        folders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]

        df = pd.DataFrame(columns=['original'] + folders)

        df['original'] = unique_originals

        for index, row in df.iterrows():
            original_path = row['original']
            for folder in folders:
                duplicate_path = duplicate_data.filter(original=original_path, duplicate__contains=folder).values_list('duplicate', flat=True)
                if duplicate_path:
                    df.at[index, folder] = duplicate_path[0]

        re_c = [selected_folder]
        df = df.drop(columns=re_c)

        for column in df.columns:
            df[column] = df[column].apply(url_to_link)

        
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)

        
        response = HttpResponse(excel_buffer.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=output.xlsx'

        return response
    

t1 = threading.Thread(target=print_square, args=('CYCLE00003',))
t1.start()
comparestatus.objects.update_or_create(cycle='CYCLE00003', defaults={'status': False})    
    
