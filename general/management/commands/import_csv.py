import csv

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from general.models import *

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('file', nargs='+', type=int)
        # Named (optional) arguments
        # parser.add_argument('--dummy',
        #                     action='store_true',
        #                     dest='dummy',
        #                     default=False,
        #                     help='Add dummy data instead of data from the .blm file.')

    def handle(self,  args, * options):
        print 'test@@'
        # self.getData()

    def getData(self):
        with open('/home/akimmel/work/employers.csv') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                print(row['ID'], row['EMPLOYER_ALIAS__C'])
                employer = Employer.objects.create(
                    id=row['ID'],
                    name=row['EMPLOYER_ALIAS__C'],
                    industry=row['EMPLOYERINDUSTRY1__C'],
                    state=row['EMPLOYERSTATE__C'],
                    size=row['EMPLOYERHEADCOUNT__C'],
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

        with open('/home/akimmel/work/life.csv') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                life = Life.objects.create(                                                 
                    id=row['ID'],
                    employer_id=row['EMPLOYERNAME__C'],
                    type=row['LP_TYPE__C'],
                    multiple=row['LP_MULTIPLE__C'],
                    multiple_max=row['LP_MULTIPLE_MAX__C'],
                    flat_amount=row['LP_FLAT_AMOUNT__C'],
                    add=row['LP_ADD__C']=='TRUE',
                    cost_share=row['LP_COST_SHARE__C'])

