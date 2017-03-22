import json
from datetime import datetime

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict
from django.db.models import Q, Avg, StdDev
from django.conf import settings
from django.utils.safestring import mark_safe

from .models import *


HEAD_COUNT = {
    'Up to 250': [0, 249],
    '250 to 499': [250, 499],
    '500 to 999': [500, 999],
    '1,000 to 4,999': [1000, 4999],
    '5,000 and Up': [5000, 2000000],
}

MODEL_MAP = {
    'LIFE': Life,
    'STD': STD
}

def get_filtered_employers(ft_industries, ft_head_counts, ft_other, ft_regions, lstart=0, lend=0, group='bnchmrk'):
    # filter with factors from UI (industry, head-count, other)
    q = Q()
    if not '*' in ft_industries:
        q = Q(industry1__in=ft_industries) | Q(industry2__in=ft_industries) | Q(industry3__in=ft_industries)

    for item in ft_other:
        if item != '*':
            q &= Q(**{item: True})

    q_region = Q()
    if not '*' in ft_regions:
        for item in ft_regions:
            q_region |= Q(**{item: True})

    q &= q_region
    q_ = Q(size=0)
    for ft_head_count in ft_head_counts:
        ft_vals = ft_head_count.split('-')        
        q_ |= Q(size__gte=int(ft_vals[0])) & Q(size__lte=int(ft_vals[1]))


    if group == "bnchmrk":
        employers_ = Employer.objects.filter(q & q_).order_by('name')
    else:
        select = {'new_name':
            'CASE WHEN broker=\'Core\' THEN name WHEN broker=\'{}\' THEN name ELSE \'De-identified Employer\' END'.format(group)}
        employers_ = Employer.objects.filter(q & q_).extra(select=select).order_by('new_name')
        
    employers = employers_
    if lend:
        employers = employers_[lstart:lend]

    num_companies = Employer.objects.filter(q & q_).count()    
    # filter with number of companies
    if num_companies < settings.EMPLOYER_THRESHOLD:
        employers = []
        # num_companies = 0

    return employers, num_companies


@csrf_exempt
@login_required(login_url='/login')
def enterprise(request):
    """
    GET: render general enterprise page
    POST: for enterprise bootgrid table
    """
    if request.method == 'POST':
        form_param = json.loads(request.body or "{}")
        limit = int(form_param.get('rowCount'))
        page = int(form_param.get('current'))
        ft_industries = form_param.get('industry_') or ['*']
        ft_head_counts = form_param.get('head_counts') or ['0-2000000']
        ft_other = form_param.get('others')
        ft_regions = form_param.get('regions')

        lstart = (page - 1) * limit
        lend = lstart + limit

        group = request.user.groups.first().name

        employers, num_companies = get_filtered_employers(ft_industries, 
                                                          ft_head_counts, 
                                                          ft_other, 
                                                          ft_regions, 
                                                          lstart, 
                                                          lend,
                                                          group)

        # convert head-count into groups
        employers_ = []
        for item in employers:
            item_ = model_to_dict(item)

            if group != 'bnchmrk':
                item_['name'] = item.new_name

            item__ = []
            if item.nonprofit:
                item__.append('Non-Profit')
            if item.govt_contractor:
                item__.append("Gov't Contractor")
            item_['other'] = '@'.join(item__)

            item__ = []
            if item.industry1:
                item__.append(item.industry1)
            if item.industry2:
                item__.append(item.industry2)
            if item.industry3:
                item__.append(item.industry3)
            item_['industry'] = '@'.join(item__)

            item__ = []
            if item.new_england:
                item__.append('New England')
            if item.mid_atlantic:
                item__.append('Tri-State Area')
            if item.south_atlantic:
                item__.append('South Atlantic')
            if item.south_cental:
                item__.append('South Central')
            if item.east_central:
                item__.append('East North Central')
            if item.west_central:
                item__.append('West North Central')
            if item.mountain:
                item__.append('Mountian')
            if item.pacific:
                item__.append('Pacific')
            item_['region'] = '@'.join(item__)

            for key, val in HEAD_COUNT.items():
                if item.size in range(val[0], val[1]):
                    item_['size'] = key
                    break
            employers_.append(item_)

        if num_companies < settings.EMPLOYER_THRESHOLD:
            num_companies = 0

        return JsonResponse({
            "current": page,
            "rowCount": limit,
            "rows": employers_,
            "total": num_companies
            }, safe=False)
    else:
        # get valid distinct industries 
        industries1 = Employer.objects.order_by('industry1').values_list('industry1').distinct()
        industries1 = [item[0] for item in industries1 if item[0]]
        industries2 = Employer.objects.order_by('industry2').values_list('industry2').distinct()
        industries2 = [item[0] for item in industries2 if item[0]]
        industries3 = Employer.objects.order_by('industry3').values_list('industry3').distinct()
        industries3 = [item[0] for item in industries3 if item[0]]
        industries = set(industries1 + industries2 + industries3)

        request.session['benefit'] = request.session.get('benefit', 'HOME')

        return render(request, 'enterprise.html', {
                'industries': sorted(industries),
                'EMPLOYER_THRESHOLD_MESSAGE': settings.EMPLOYER_THRESHOLD_MESSAGE
            })
        

@csrf_exempt
def ajax_enterprise(request):
    """
    get body of page
    supposed to be called for only real template not print
    """
    form_param = request.POST
    ft_industries = form_param.getlist('industry[]', ['*'])
    ft_head_counts = form_param.getlist('head_counts[]') or ['0-2000000']
    ft_other = form_param.getlist('others[]')
    ft_regions = form_param.getlist('regions[]')

    ft_industries_label = form_param.getlist('industry_label[]')
    ft_head_counts_label = form_param.getlist('head_counts_label[]')
    ft_other_label = form_param.getlist('others_label[]')
    ft_regions_label = form_param.getlist('regions_label[]')

    benefit = form_param.get('benefit')

    # store for print
    request.session['benefit'] = benefit
    request.session['ft_industries'] = ft_industries
    request.session['ft_head_counts'] = ft_head_counts
    request.session['ft_other'] = ft_other
    request.session['ft_regions'] = ft_regions

    request.session['ft_industries_label'] = ft_industries_label
    request.session['ft_head_counts_label'] = ft_head_counts_label
    request.session['ft_other_label'] = ft_other_label
    request.session['ft_regions_label'] = ft_regions_label

    if benefit == 'HOME':
        full_name = '{} {}'.format(request.user.first_name, request.user.last_name)
        return render(request, 'home.html', locals())
    elif benefit == 'LIFE':
        employers, num_companies = get_filtered_employers(ft_industries, 
                                                          ft_head_counts, 
                                                          ft_other,
                                                          ft_regions)
        context = get_life_plan(employers, num_companies)
        context['base_template'] = 'empty.html'
        context['today'] = datetime.strftime(datetime.now(), '%B %d, %Y')
        return render(request, 'life_plan.html', context)
    elif benefit == 'EMPLOYERS':
        return render(request, 'employers.html')
    return HttpResponse('Nice')


@csrf_exempt
def update_properties(request):
    form_param = request.POST
    benefit = form_param.get('benefit')
    plan = int(form_param.get('plan', 0))

    # save for print
    if plan != -1:
        request.session['plan'] = plan
    else:
        plan = request.session['plan']

    func_name = 'get_{}_properties'.format(benefit.lower())
    return globals()[func_name](request, plan)


def get_life_properties(request, plan):
    context = {}
    multiple_max = 'N/A'
    flat_amount = 'N/A'
    multiple = 'N/A'
    add_flat = 'N/A'
    add_multiple = 'N/A'
    rank_flat = 'N/A'
    rank_multiple = 'N/A'

    if plan:
        ft_industries = request.session['ft_industries']
        ft_head_counts = request.session['ft_head_counts']
        ft_other = request.session['ft_other']
        ft_regions = request.session['ft_regions']

        employers, num_companies = get_filtered_employers(ft_industries, 
                                                          ft_head_counts, 
                                                          ft_other,
                                                          ft_regions)

        lifes = Life.objects.filter(employer__in=employers)
        life = Life.objects.get(id=plan)
        multiple_max = '${:,.0f}'.format(life.multiple_max) if life.multiple_max else 'N/A'
        flat_amount = '${:,.0f}'.format(life.flat_amount) if life.flat_amount else 'N/A'
        multiple = life.multiple or 'N/A'
        
        if life.type == 'Flat Amount':
            add_flat = 'Yes' if life.add else 'No'
            if life.flat_amount:
                qs_flat_amount = lifes.exclude(flat_amount__isnull=True)
                quintile_array_flat = get_incremental_array(qs_flat_amount, 'flat_amount') 
                rank_flat = get_rank(quintile_array_flat, life.flat_amount)
        else:
            add_multiple = 'Yes' if life.add else 'No'
            if life.multiple_max:
                qs_multiple_max = lifes.exclude(multiple_max__isnull=True)
                quintile_array_multiple = get_incremental_array(qs_multiple_max, 'multiple_max') 
                rank_multiple = get_rank(quintile_array_multiple, life.multiple_max)

    context['multiple_max'] = multiple_max
    context['flat_amount'] = flat_amount
    context['multiple'] = multiple
    context['add_flat'] = add_flat
    context['add_multiple'] = add_multiple
    context['rank_flat'] = rank_flat
    context['rank_multiple'] = rank_multiple
    return JsonResponse(context, safe=False)


def get_rank(quintile_array, value):
    x_vals = []
    for idx in range(len(quintile_array)-1):
        if quintile_array[idx][1] <= value and value <= quintile_array[idx+1][1]:
            x_vals.append(quintile_array[idx+1][0])

    x_mean = 0
    for item in x_vals:
        x_mean += item
    x_mean = x_mean * 1.0 / len(x_vals)

    for idx in range(1, 6):
        if x_mean < idx * 20:
            return idx


def get_life_plan(employers, num_companies):
    if num_companies < settings.EMPLOYER_THRESHOLD:
        return {
            'EMPLOYER_THRESHOLD_MESSAGE': settings.EMPLOYER_THRESHOLD_MESSAGE,
            'num_employers': num_companies,
            'EMPLOYER_THRESHOLD': settings.EMPLOYER_THRESHOLD
        }

    lifes = Life.objects.filter(employer__in=employers)
    num_lifes = lifes.count()


    qs_multiple = lifes.exclude(multiple__isnull=True)
    mdn_multiple, cnt_multiple = get_median_count(qs_multiple, 'multiple')
    qs_multiple_max = lifes.exclude(multiple_max__isnull=True)
    mdn_multiple_max, cnt_multiple_max = get_median_count(qs_multiple_max, 'multiple_max')
    qs_flat_amount = lifes.exclude(flat_amount__isnull=True)
    mdn_flat_amount, cnt_flat_amount = get_median_count(qs_flat_amount, 'flat_amount')    

    # for counting # of plans
    num_plan0 = employers.filter(life_count=0).count()
    num_plan1 = employers.filter(life_count=1).count()
    num_plan2 = employers.filter(life_count=2).count()
    num_plan3_or_more = num_companies - num_plan0 - num_plan1 - num_plan2

    prcnt_plan0 = '{0:0.0f}'.format(num_plan0 * 100.0 / num_companies)
    prcnt_plan1 = '{0:0.0f}'.format(num_plan1 * 100.0 / num_companies)
    prcnt_plan2 = '{0:0.0f}'.format(num_plan2 * 100.0 / num_companies)
    prcnt_plan3_or_more = '{0:0.0f}'.format(num_plan3_or_more * 100.0 / num_companies)

    quintile_array_flat = get_incremental_array(qs_flat_amount, 'flat_amount') 
    quintile_array_multiple = get_incremental_array(qs_multiple_max, 'multiple_max') 
    
    cnt_add_flat = lifes.filter(add=True, type='Flat Amount').count()
    cnt_add_flat_ = lifes.filter(type='Flat Amount').count()
    cnt_add_multiple = lifes.filter(add=True, type='Multiple of Salary').count()
    cnt_add_multiple_ = lifes.filter(type='Multiple of Salary').count()

    companies_with_mul_plan = set([item.employer_id for item in lifes.filter(type='Multiple of Salary')])
    companies_with_flat_plan = set([item.employer_id for item in lifes.filter(type='Flat Amount')])

    cnt_type_plan_none = num_plan0
    cnt_type_plan_mul = len(companies_with_mul_plan - companies_with_flat_plan)
    cnt_type_plan_flat = len(companies_with_flat_plan - companies_with_mul_plan)
    cnt_type_plan_mul_flat = len(companies_with_flat_plan.intersection(companies_with_mul_plan))
    cnt_type_non_reported = -(cnt_type_plan_mul_flat + cnt_type_plan_none + cnt_type_plan_mul + cnt_type_plan_flat - num_companies)

    companies_with_paid = set([item.employer_id for item in lifes.filter(cost_share='100% Employer Paid')])
    companies_with_share = set([item.employer_id for item in lifes.filter(cost_share='Employee Cost Share')])
    cnt_paid = len(companies_with_paid - companies_with_share)
    cnt_share = len(companies_with_share - companies_with_paid)
    cnt_paid_share = len(companies_with_share.intersection(companies_with_paid))
    cnt_non_reported = num_companies - num_plan0 - cnt_paid - cnt_share - cnt_paid_share

    prcnt_add_flat = '{0:0.0f}%'.format(cnt_add_flat * 100.0 / cnt_add_flat_)
    prcnt_add_multiple = '{0:0.0f}%'.format(cnt_add_multiple * 100.0 / cnt_add_multiple_)
    prcnt_type_plan_none = '{0:0.0f}'.format(cnt_type_plan_none * 100.0 / num_companies)
    prcnt_type_plan_mul = '{0:0.0f}'.format(cnt_type_plan_mul * 100.0 / num_companies)
    prcnt_type_plan_flat = '{0:0.0f}'.format(cnt_type_plan_flat * 100.0 / num_companies)
    prcnt_type_plan_mul_flat = '{0:0.0f}'.format(cnt_type_plan_mul_flat * 100.0 / num_companies)
    prcnt_type_non_reported = '{0:0.0f}'.format(cnt_type_non_reported * 100.0 / num_companies)

    prcnt_paid = '{0:0.0f}'.format(cnt_paid * 100.0 / num_companies)
    prcnt_share = '{0:0.0f}'.format(cnt_share * 100.0 / num_companies)
    prcnt_paid_share = '{0:0.0f}'.format(cnt_paid_share * 100.0 / num_companies)    
    prcnt_non_reported = '{0:0.0f}'.format(cnt_non_reported * 100.0 / num_companies)    

    return {
        'EMPLOYER_THRESHOLD': settings.EMPLOYER_THRESHOLD,
        'EMPLOYER_THRESHOLD_MESSAGE': settings.EMPLOYER_THRESHOLD_MESSAGE,
        'num_employers': num_companies,
        
        'mdn_multiple': mdn_multiple,
        'mdn_multiple_max': mdn_multiple_max, 
        'mdn_flat_amount': mdn_flat_amount, 

        'quintile_array_flat': mark_safe(json.dumps(quintile_array_flat)),
        'quintile_array_multiple': mark_safe(json.dumps(quintile_array_multiple)),        
        
        'prcnt_add_flat': prcnt_add_flat,
        'prcnt_add_multiple': prcnt_add_multiple,
        'prcnt_type_plan_none': prcnt_type_plan_none,
        'prcnt_type_plan_mul': prcnt_type_plan_mul,
        'prcnt_type_plan_flat': prcnt_type_plan_flat,
        'prcnt_type_plan_mul_flat': prcnt_type_plan_mul_flat,
        'prcnt_type_non_reported': prcnt_type_non_reported,
        'prcnt_paid': prcnt_paid,
        'prcnt_share': prcnt_share,
        'prcnt_paid_share': prcnt_paid_share,
        'prcnt_non_reported': prcnt_non_reported,        
        'prcnt_plan0': prcnt_plan0,
        'prcnt_plan1': prcnt_plan1,
        'prcnt_plan2': prcnt_plan2,
        'prcnt_plan3_or_more': prcnt_plan3_or_more,
    }


@csrf_exempt
def get_num_employers(request):
    form_param = request.POST
    ft_industries = form_param.getlist('industry[]', ['*'])
    ft_head_counts = form_param.getlist('head_counts[]') or ['0-2000000']
    ft_other = form_param.getlist('others[]')
    ft_regions = form_param.getlist('regions[]')
    benefit = form_param.get('benefit')

    employers, num_companies = get_filtered_employers(ft_industries, 
                                                      ft_head_counts, 
                                                      ft_other,
                                                      ft_regions)
    return HttpResponse(num_companies or "<25")


def get_median_count(queryset, term):
    count = queryset.count()
    values = queryset.values_list(term, flat=True).order_by(term)
    if count % 2 == 1:
        return values[int(round(count/2))], count
    else:
        return sum(values[count/2-1:count/2+1])/2, count


def get_incremental_array(queryset, term):
    num_points = settings.MAX_POINTS
    num_elements = queryset.count()

    interval = num_elements / num_points + 1 #if num_elements > num_points else 1

    # limit number of points as MAX_POINTS
    result = []
    idx = 0
    idx_ = 0

    for item in queryset.order_by(term):
        if idx % interval == 0:
            # result.append([idx_, getattr(item, term)])
            result.append(getattr(item, term))            
            idx_ += 1
        idx += 1
        # store last maximum value
        if idx == num_elements:
            last_value = getattr(item, term)

    # format labels for 20%, 40% ..., 100%
    idx = 0
    factor = 20
    num_points = len(result)
    result_ = []
    label_o = 0

    for item in result:
        label_ = int(idx * 100 / num_points)
        if label_o < factor and factor <= label_:
            label_ = factor
            factor += 20 
        label = '{}%'.format(label_)
        # result_.append([label, item])
        result_.append([label_, item])
        label_o = label_
        idx += 1

    result_[-1] = [100, last_value]
    return result_


@csrf_exempt
def get_plans(request):
    benefit = request.POST.get('benefit')
    group = request.user.groups.first().name

    allowed_benefits = ['LIFE']
    plans = []
    if benefit in allowed_benefits:
        plans = get_plans_(benefit, group)

    return render(request, 'plans.html', { 'plans': plans })


def get_plans_(benefit, group):
    model = MODEL_MAP[benefit]
    if group == 'bnchmrk':
        objects = model.objects.all()
    else:
        objects = model.objects.filter(employer__broker=group)

    return [
               [item.id, '{} - {}'.format(item.employer.name, item.title)]
               for item in objects.order_by('employer__name', 'title')
           ]
