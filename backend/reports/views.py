from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import VehicleReport, ReportLookup, OwnedVehicle
from .validators import validate_vin
from .tasks import fetch_vehicle_report
from .services.pdf_generator import generate_report_pdf


class VehicleReportSerializer(serializers.ModelSerializer):
    class Meta:
        model  = VehicleReport
        fields = [
            'vin', 'raw_data', 'risk_score', 'accident_count',
            'owner_count', 'has_salvage_title', 'has_flood_damage',
            'open_recall_count', 'last_reported_odometer', 'created_at',
        ]


class VehicleReportView(APIView):

    def post(self, request):
        if not request.user.can_lookup:
            return Response({
                'error':   'no_access',
                'message': 'Purchase a lookup or subscribe to continue.',
            }, status=status.HTTP_402_PAYMENT_REQUIRED)

        vin = request.data.get('vin', '').strip().upper()
        valid, error = validate_vin(vin)
        if not valid:
            return Response({'error': error}, status=400)

        report_obj = VehicleReport.objects.filter(vin=vin).first()
        if not report_obj:
            data = fetch_vehicle_report(vin)
            report_obj = VehicleReport.objects.create(
                vin=vin,
                raw_data=data,
                risk_score=data['risk_score'],
                accident_count=data.get('accident_count', 0),
                owner_count=data.get('owner_count'),
                has_salvage_title='salvage' in data.get('title_flags', []),
                has_flood_damage='flood'    in data.get('title_flags', []),
                open_recall_count=len(data.get('recalls', [])),
                last_reported_odometer=data.get('last_reported_odometer'),
            )

        # Deduct credit if not subscriber and not dealer
        from users.models import User
        from django.db.models import F
        u = request.user
        if u.subscription_status != 'active' and not (
            hasattr(u, 'dealer_profile') and u.dealer_profile.is_active
        ):
            User.objects.filter(id=u.id).update(lookup_credits=F('lookup_credits') - 1)

        # Track dealer usage
        if hasattr(u, 'dealer_profile') and u.dealer_profile.is_active:
            from users.models import DealerProfile
            DealerProfile.objects.filter(user=u).update(
                monthly_lookups=F('monthly_lookups') + 1
            )

        ReportLookup.objects.create(user=request.user, report=report_obj)
        return Response({'success': True, 'data': VehicleReportSerializer(report_obj).data})


class UserReportHistoryView(APIView):
    def get(self, request):
        lookups = (
            ReportLookup.objects
            .filter(user=request.user)
            .select_related('report')
        )
        return Response({'reports': [
            VehicleReportSerializer(l.report).data for l in lookups
        ]})


class ReportPDFView(APIView):
    def get(self, request, vin):
        report_obj = get_object_or_404(VehicleReport, vin=vin.upper())

        if not ReportLookup.objects.filter(
            user=request.user, report=report_obj
        ).exists():
            return Response({'error': 'Not found.'}, status=404)

        dealer_brand = None
        if hasattr(request.user, 'dealer_profile'):
            d = request.user.dealer_profile
            dealer_brand = {
                'name':  d.business_name,
                'color': d.brand_color,
            }

        pdf_bytes = generate_report_pdf(report_obj.raw_data, dealer_brand)
        response  = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="VINScan-{vin}.pdf"'
        return response


class BatchVINLookupView(APIView):
    """Dealer-only: submit up to 50 VINs at once."""

    def post(self, request):
        if not (hasattr(request.user, 'dealer_profile') and
                request.user.dealer_profile.is_active):
            return Response({'error': 'Dealer account required.'}, status=403)

        vins = request.data.get('vins', [])
        if not isinstance(vins, list) or not (1 <= len(vins) <= 50):
            return Response({'error': 'Provide 1–50 VINs as a list.'}, status=400)

        from django.db.models import F
        from users.models import DealerProfile
        results = []

        for raw_vin in vins:
            vin   = raw_vin.strip().upper()
            valid, error = validate_vin(vin)
            if not valid:
                results.append({'vin': vin, 'error': error})
                continue

            report_obj = VehicleReport.objects.filter(vin=vin).first()
            if not report_obj:
                data = fetch_vehicle_report(vin)
                report_obj = VehicleReport.objects.create(
                    vin=vin, raw_data=data, risk_score=data['risk_score'],
                    accident_count=data.get('accident_count', 0),
                    owner_count=data.get('owner_count'),
                    has_salvage_title='salvage' in data.get('title_flags', []),
                    has_flood_damage='flood'    in data.get('title_flags', []),
                    open_recall_count=len(data.get('recalls', [])),
                    last_reported_odometer=data.get('last_reported_odometer'),
                )

            ReportLookup.objects.get_or_create(user=request.user, report=report_obj)
            v = report_obj.raw_data.get('vehicle', {})
            results.append({
                'vin':         vin,
                'risk_score':  report_obj.risk_score,
                'make':        v.get('make'),
                'model':       v.get('model'),
                'year':        v.get('year'),
                'accidents':   report_obj.accident_count,
                'title_clean': not report_obj.has_salvage_title and not report_obj.has_flood_damage,
                'recalls':     report_obj.open_recall_count,
                'pdf_url':     f'/api/report/{vin}/pdf/',
            })

        DealerProfile.objects.filter(user=request.user).update(
            monthly_lookups=F('monthly_lookups') + len(vins)
        )

        return Response({'results': results, 'count': len(results)})


class DealerUsageView(APIView):

    def get(self, request):
        if not hasattr(request.user, 'dealer_profile'):
            return Response({'error': 'Not a dealer account.'}, status=403)
        d = request.user.dealer_profile
        return Response({
            'business_name':   d.business_name,
            'brand_color':     d.brand_color,
            'logo_url':        d.logo_url,
            'monthly_lookups': d.monthly_lookups,
            'is_active':       d.is_active,
        })

    def patch(self, request):
        if not hasattr(request.user, 'dealer_profile'):
            return Response({'error': 'Not a dealer account.'}, status=403)
        d = request.user.dealer_profile
        d.business_name = request.data.get('business_name', d.business_name)
        d.brand_color   = request.data.get('brand_color',   d.brand_color)
        d.logo_url      = request.data.get('logo_url',      d.logo_url)
        d.save()
        return Response({'success': True})


class OwnedVehicleView(APIView):

    def get(self, request):
        owned  = OwnedVehicle.objects.filter(user=request.user)
        result = []
        for o in owned:
            report = VehicleReport.objects.filter(vin=o.vin).first()
            result.append({
                'vin':          o.vin,
                'nickname':     o.nickname,
                'added_at':     o.added_at,
                'risk_score':   report.risk_score if report else None,
                'open_recalls': report.open_recall_count if report else 0,
                'vehicle':      report.raw_data.get('vehicle') if report else None,
            })
        return Response({'owned': result})

    def post(self, request):
        vin      = request.data.get('vin', '').upper()
        nickname = request.data.get('nickname', '')
        valid, error = validate_vin(vin)
        if not valid:
            return Response({'error': error}, status=400)
        obj, created = OwnedVehicle.objects.get_or_create(
            user=request.user, vin=vin,
            defaults={'nickname': nickname},
        )
        return Response({'success': True, 'created': created})

    def delete(self, request, vin):
        OwnedVehicle.objects.filter(user=request.user, vin=vin.upper()).delete()
        return Response({'success': True})
