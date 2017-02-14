from __future__ import unicode_literals

from django.db import models

# Create your models here.

class Employer(models.Model):
    id = models.CharField(max_length=18, primary_key=True)
    name = models.CharField(max_length=100)
    alias = models.CharField(max_length=100) 
    broker = models.CharField(max_length=75) 
    industry1 = models.CharField(max_length=75)
    industry2 = models.CharField(max_length=75) 
    industry3 = models.CharField(max_length=75) 
    state = models.CharField(max_length=25)
    size = models.IntegerField(blank=True, null=True)
    nonprofit = models.BooleanField()
    govt_contractor = models.BooleanField()
    new_england = models.BooleanField()
    mid_atlantic = models.BooleanField()
    south_atlantic = models.BooleanField()
    south_cental = models.BooleanField()
    east_central = models.BooleanField()
    west_central = models.BooleanField()
    mountain = models.BooleanField()
    pacific = models.BooleanField()
    med_count = models.IntegerField() 
    den_count = models.IntegerField() 
    vis_count = models.IntegerField() 
    life_count = models.IntegerField() 
    std_count = models.IntegerField() 
    ltd_count = models.IntegerField() 

    def __unicode__(self):
        return self.name


class Life(models.Model):
    employer = models.ForeignKey(Employer)
    type = models.CharField(max_length=18)
    multiple = models.FloatField(blank=True, null=True)
    multiple_max = models.IntegerField(blank=True, null=True)
    flat_amount = models.IntegerField(blank=True, null=True)
    add = models.BooleanField()
    cost_share = models.CharField(max_length=19)

    def __unicode__(self):
        return self.employer.name
        
    class Meta:
        verbose_name_plural = 'Life Plans'
    

class STD(models.Model):
    employer = models.ForeignKey(Employer)
    salary_cont = models.BooleanField()
    waiting_days = models.IntegerField(blank=True, null=True)
    waiting_days_sick = models.IntegerField(blank=True, null=True)
    duration_weeks = models.IntegerField(blank=True, null=True)
    percentage = models.IntegerField(blank=True, null=True)
    weekly_max = models.IntegerField(blank=True, null=True)
    cost_share = models.CharField(max_length=19)

    def __unicode__(self):
        return self.employer.name
        
    class Meta:
        verbose_name_plural = 'STD Plans'
    
    