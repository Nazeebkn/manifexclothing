from django.shortcuts import render, redirect
from django.contrib import messages
from .models import ContactSubmission

def contact(request):
    if request.method == 'POST':
        # Retrieve form data
        first_name = request.POST.get('firstname')
        last_name = request.POST.get('lastname')
        phone_number = request.POST.get('number')
        email = request.POST.get('email')
        message = request.POST.get('message')

        # Basic validation
        if not all([first_name, last_name, phone_number, email, message]):
            messages.error(request, 'All fields are required.')
            return render(request, 'contact.html')

        # Save form data to the database
        try:
            ContactSubmission.objects.create(
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                email=email,
                message=message
            )
            messages.success(request, 'Your message has been sent successfully!')
            return redirect('contact')
        except Exception as e:
            messages.error(request, 'An error occurred while submitting your form. Please try again.')
            return render(request, 'contact.html')

    return render(request, 'contact.html')


def about(request):
    return render(request, 'about.html')