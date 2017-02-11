import csv
import json

from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict
from django.db.models import Q

from .models import *


HEAD_COUNT = {
    'Up to 250': [0, 249],
    '250 to 499': [250, 499],
    '500 to 999': [500, 999],
    '1,000 to 4,999': [1000, 4999],
    '5,000 and Up': [5000, 2000000],
}

def user_login(request):
    if request.method == 'GET':
        return render(request, 'login.html')
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse('enterprise'))
        else:
            message = 'Your login credential is not correct! Please try again.'
            return render(request, 'login.html', {
                'message': message,
            })


def user_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse('login')) 


def import_data(request):
    with open('/home/akimmel/work/employers.csv') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                if not Employer.objects.filter(id=row['ID']).exists():
                    employer = Employer.objects.create(
                        id=row['ID'],
                        name=row['EMPLOYER_ALIAS__C'],
                        industry=row['EMPLOYERINDUSTRY1__C'],
                        state=row['EMPLOYERSTATE__C'],
                        size=row['EMPLOYERHEADCOUNT__C'] or None,
                        nonprofit=row['NON_PROFIT__C']=='TRUE',
                        govt_contractor=row['GOVT_CONTRACTOR__C']=='TRUE',
                        new_england=row['DISTRICT_NEW_ENGLAND__C']=='TRUE',
                        mid_atlantic=row['DISTRICT_MID_ATLANTIC__C']=='TRUE',
                        south_atlantic=row['DISTRICT_SOUTH_ATLANTIC__C']=='TRUE',
                        south_cental=row['DISTRICT_SOUTH_CENTRAL__C']=='TRUE',
                        east_central=row['DISTRICT_EAST_NORTH_CENTRAL__C']=='TRUE',
                        west_central=row['DISTRICT_WEST_NORTH_CENTRAL__C']=='TRUE',
                        mountain=row['DISTRICT_MOUNTAIN__C']=='TRUE',
                        pacific=row['DISTRICT_PACIFIC__C']=='TRUE')
            except Exception as e:
                print row['ID'], '#{}#'.format(row['EMPLOYERHEADCOUNT__C'])

    with open('/home/akimmel/work/life.csv') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                if not Life.objects.filter(id=row['ID']).exists():
                    life = Life.objects.create(                                                 
                        id=row['ID'],
                        employer_id=row['EMPLOYERNAME__C'],
                        type=row['LP_TYPE__C'],
                        multiple=row['LP_MULTIPLE__C'] or None,
                        multiple_max=row['LP_MULTIPLE_MAX__C'] or None,
                        flat_amount=row['LP_FLAT_AMOUNT__C'] or None,
                        add=row['LP_ADD__C']=='TRUE',
                        cost_share=row['LP_COST_SHARE__C'])
            except Exception as e:
                print row['ID'], '#{}#'.format(row['LP_MULTIPLE__C'])
                # raise

    return HttpResponse('Successfully imported!')


def get_filtered_employers(ft_industries, ft_head_counts, lstart=0, lend=0):
    # filter with factors from UI (industry, head-count)
    q = Q()
    if not '*' in ft_industries:
        q &= Q(industry__in=ft_industries)

    q_ = Q(size=0)
    for ft_head_count in ft_head_counts:
        ft_vals = ft_head_count.split('-')        
        q_ |= Q(size__gte=int(ft_vals[0])) & Q(size__lte=int(ft_vals[1]))

    if lend:
        employers = Employer.objects.filter(q & q_).order_by('name')[lstart:lend]
    else:
        employers = Employer.objects.filter(q & q_).order_by('name')

    num_companies = Employer.objects.filter(q & q_).count()    
    # filter with number of companies
    if num_companies < 25:
        employers = []
        num_companies = 0

    return employers, num_companies


@csrf_exempt
@login_required(login_url='/login')
def enterprise(request):
    if request.method == 'POST':
        form_param = json.loads(request.body or "{}")
        limit = int(form_param.get('rowCount'))
        page = int(form_param.get('current'))
        ft_industries = form_param.get('industry_') or ['*']
        ft_head_counts = form_param.get('head_counts') or ['0-2000000']

        lstart = (page - 1) * limit
        lend = lstart + limit

        employers, num_companies = get_filtered_employers(ft_industries, ft_head_counts, lstart, lend)

        # convert head-count into groups
        employers_ = []
        for item in employers:
            item_ = model_to_dict(item)
            
            item_['nonprofit'] = 'TRUE' if item.nonprofit else ''
            item_['govt_contractor'] = 'TRUE' if item.govt_contractor else ''

            for key, val in HEAD_COUNT.items():
                if item.size in range(val[0], val[1]):
                    item_['size'] = key
                    break
            employers_.append(item_)

        return JsonResponse({
            "current": page,
            "rowCount": limit,
            "rows": employers_,
            "total": num_companies
            }, safe=False)
    else:
        # get valid distinct industries 
        industries = Employer.objects.order_by('industry').values_list('industry').distinct()
        industries = [item[0] for item in industries if item[0]]

        return render(request, 'enterprise.html', 
            {'industries': industries})
        

@csrf_exempt
def ajax_enterprise(request):
    form_param = request.POST
    ft_industries = form_param.getlist('industry[]', ['*'])
    ft_head_counts = form_param.getlist('head_counts[]') or ['0-2000000']
    benefit = form_param.get('benefit')

    employers, num_companies = get_filtered_employers(ft_industries, ft_head_counts)

    if benefit == 'LIFE':
        medians, counts = get_life_plan(employers)
        return render(request, 'life_plan.html', {'medians': medians, 'counts': counts})
    elif benefit == 'EMPLOYERS':
        return render(request, 'employers.html')
    return HttpResponse('Nice')


def get_life_plan(employers):
    counts = []
    medians = []
    if not employers:
        return medians, counts

    lifes = Life.objects.filter(employer__in=employers)
    qs_multiple = lifes.exclude(multiple__isnull=True)
    median, count = get_median_count(qs_multiple, 'multiple')
    medians.append(median)
    counts.append(count)
    qs_multiple_max = lifes.exclude(multiple_max__isnull=True)
    median, count = get_median_count(qs_multiple_max, 'multiple_max')
    medians.append(median)
    counts.append(count)
    qs_flat_amount = lifes.exclude(flat_amount__isnull=True)
    median, count = get_median_count(qs_flat_amount, 'flat_amount')
    medians.append(median)
    counts.append(count)

    return medians, counts


def get_median_count(queryset, term):
    count = queryset.count()
    values = queryset.values_list(term, flat=True).order_by(term)
    if count % 2 == 1:
        return values[int(round(count/2))], count
    else:
        return sum(values[count/2-1:count/2+1])/2.0, count