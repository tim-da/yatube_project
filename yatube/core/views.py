from django.shortcuts import render


def page_403(request, exception):
    return render(request, '403.html', status=403)


def page_404(request, exception):
    return render(request, '404.html', status=404)


def page_500(request):
    return render(request, '500.html', status=500)
