
# Create your views here.

from django.shortcuts import render,redirect,get_object_or_404
from .models import categories
from django.contrib import messages
from .forms import categoryform
from PIL import Image
from django.core.files.base import ContentFile
from io import BytesIO
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import categories
import io


@login_required
@never_cache
def category_list(request):
   
    search_query = request.GET.get('search', '')      
    if search_query:
        all_categories = categories.objects.filter(name__icontains=search_query)
    else:
        all_categories = categories.objects.all()    
    active_categories = all_categories.filter(is_listed=True)
    inactive_categories = all_categories.filter(is_listed=False)
    
   
    paginator = Paginator(all_categories, 10)  
    page_number = request.GET.get('page')
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    context = {
        'page_obj': page_obj, 
        'search_query': search_query, 
        'active_categories': active_categories, 
        'inactive_categories': inactive_categories, 
    }
    
    return render(request, 'category_list.html', context)

@never_cache
@staff_member_required
def add_category(request):
  if request.method=='POST':
    form=categoryform(request.POST,request.FILES)
    name=request.POST.get('name')

    if categories.objects.filter(name__iexact=name).exists():
        messages.error(request, "Category already exists")
        return render(request, 'add_category.html', {'form': form})
    
    if form.is_valid():
      category= form.save(commit=False)

      uploaded_image = form.cleaned_data.get('image')
      if uploaded_image:
        image = Image.open(uploaded_image)
        width, height = image.size
        new_size = min(width, height)
        left = (width - new_size) / 2
        top = (height - new_size) / 2
        right = (width + new_size) / 2
        bottom = (height + new_size) / 2
        cropped_image = image.crop((left, top, right, bottom))
        buffer = BytesIO()
        cropped_image.save(buffer, format=image.format)
        category.image.save(uploaded_image.name, ContentFile(buffer.getvalue()), save=False)

      category.save()
      messages.success(request, f"Category '{category.name}' added successfully.")
      return redirect('category_list')
      
    else:
        messages.error(request, "Please correct the errors below.")
  else:
    form=categoryform()

  return render(request,'add_category.html',{'form': form})



@staff_member_required
@never_cache
def edit_category(request, id):
    category = get_object_or_404(categories, id=id)

    if request.method == 'POST':
        form = categoryform(request.POST, request.FILES, instance=category)

        if form.is_valid():
            category = form.save(commit=False)
            print("haloooooooo")
            if 'image' in request.FILES:
                print("haloooo")
                uploaded_image = request.FILES['image'] 
                image = Image.open(uploaded_image)
                width, height = image.size
                new_size = min(width, height)
                left = (width - new_size) / 2
                top = (height - new_size) / 2
                right = (width + new_size) / 2
                bottom = (height + new_size) / 2
                cropped_image = image.crop((left, top, right, bottom))
                buffer = io.BytesIO()
                cropped_image.save(buffer, format=image.format)
                category.image.save(uploaded_image.name, ContentFile(buffer.getvalue()), save=False)

            category.save()
            return redirect('category_list')
    else:
        form = categoryform(instance=category)

    return render(request, 'edit_category.html', {'form': form, 'category': category})



@login_required
@never_cache
def unlist_category(request, id):
    category = get_object_or_404(categories, id=id)
    category.is_listed = not category.is_listed  
    category.save()
    status = "listed" if category.is_listed else "unlisted"
    messages.success(request, f"Category {category.name} has been {status}.")
    return redirect('category_list')