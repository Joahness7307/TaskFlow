import json
from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator
from django.db.models import F, Q, Case, When, Value, IntegerField
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from .models import Task


def landing(request):
    if request.user.is_authenticated:
        return redirect("task_list")
    return render(request, "landing.html")


def _parse_due_date(due_date_value):
    if not due_date_value:
        return None
    try:
        return datetime.strptime(due_date_value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


@login_required
def task_list(request):
    tasks = Task.objects.filter(user=request.user)

    search_query = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "all").strip().lower()
    month_filter = request.GET.get("month", "").strip()
    sort_option = request.GET.get("sort", "created_date").strip().lower()

    if search_query:
        tasks = tasks.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )

    if status_filter == "completed":
        tasks = tasks.filter(is_completed=True)
    elif status_filter == "pending":
        tasks = tasks.filter(is_completed=False)
    else:
        status_filter = "all"

    if month_filter:
        try:
            year_str, month_str = month_filter.split("-")
            year = int(year_str)
            month = int(month_str)
            tasks = tasks.filter(created_at__year=year, created_at__month=month)
        except (ValueError, TypeError):
            month_filter = ""

    if sort_option == "due_date":
        tasks = tasks.order_by(F("due_date").asc(nulls_last=True), "-created_at")
    elif sort_option == "priority":
        tasks = tasks.annotate(
            priority_sort=Case(
                When(priority=Task.PRIORITY_URGENT, then=Value(1)),
                When(priority=Task.PRIORITY_HIGH, then=Value(2)),
                When(priority=Task.PRIORITY_MEDIUM, then=Value(3)),
                When(priority=Task.PRIORITY_LOW, then=Value(4)),
                default=Value(5),
                output_field=IntegerField(),
            )
        ).order_by("priority_sort", "-created_at")
    elif sort_option == "title":
        tasks = tasks.order_by("title")
    else:
        sort_option = "created_date"
        tasks = tasks.order_by("-created_at")

    paginator = Paginator(tasks, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()
    query_params.pop("page", None)

    context = {
        "tasks": page_obj,
        "page_obj": page_obj,
        "search_query": search_query,
        "status_filter": status_filter,
        "month_filter": month_filter,
        "sort_option": sort_option,
        "today": date.today(),
        "available_months": tasks.model.objects.filter(user=request.user).dates(
            "created_at", "month", order="DESC"
        ),
        "query_params": query_params.urlencode(),
    }
    return render(request, "tasks/task_list.html", context)


@login_required
def create_task(request):
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        due_date = _parse_due_date(request.POST.get("due_date"))
        priority = request.POST.get("priority", Task.PRIORITY_MEDIUM)
        if priority not in dict(Task.PRIORITY_CHOICES):
            priority = Task.PRIORITY_MEDIUM
        is_completed = request.POST.get("is_completed") == "on"
        Task.objects.create(
            user=request.user,
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            is_completed=is_completed,
        )
        messages.success(request, "Task created successfully!")
        return redirect("task_list")
    return redirect("task_list")


@login_required
def task_edit(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)

    if request.method == 'POST':
        task.title = request.POST.get('title')
        task.description = request.POST.get('description')
        task.due_date = _parse_due_date(request.POST.get("due_date"))
        priority = request.POST.get("priority", Task.PRIORITY_MEDIUM)
        if priority in dict(Task.PRIORITY_CHOICES):
            task.priority = priority
        else:
            task.priority = Task.PRIORITY_MEDIUM
        task.is_completed = request.POST.get('is_completed') == 'on'
        task.save()
        messages.success(request, 'Task updated successfully!')
        return redirect('task_list')

    return redirect('task_list')


@login_required
def task_delete(request, task_id):
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id, user=request.user)
        task.delete()
        messages.success(request, 'Task deleted successfully!')

    return redirect('task_list')


@login_required
def task_toggle_completion(request, task_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)

    task = get_object_or_404(Task, id=task_id, user=request.user)
    completed_value = request.POST.get("completed")

    if completed_value is None:
        try:
            payload = json.loads(request.body.decode("utf-8"))
            completed_value = payload.get("completed")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({"success": False, "error": "Invalid payload"}, status=400)

    if isinstance(completed_value, bool):
        is_completed = completed_value
    else:
        is_completed = str(completed_value).lower() == "true"

    task.is_completed = is_completed
    task.save(update_fields=["is_completed"])

    is_overdue = bool(task.due_date and task.due_date < date.today() and not task.is_completed)
    return JsonResponse(
        {"success": True, "is_completed": task.is_completed, "is_overdue": is_overdue}
    )


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("task_list")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("login")
    else:
        form = UserCreationForm()

    return render(request, "registration/signup.html", {"form": form})