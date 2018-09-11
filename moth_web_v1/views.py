from django.shortcuts import render

def index(request):
    """MOTH index page"""
    return render(request, 'moth_web_v1/index.html')


def credits(request):
    """MOTH credits page"""
    return render(request, 'moth_web_v1/credits.html')


def puzzles(request):
    """MOTH puzzles page"""
    return render(request, 'moth_web_v1/puzzles.html')
