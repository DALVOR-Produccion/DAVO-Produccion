"""Catálogo y material completo con autorización comprobada en servidor."""
from datetime import date, datetime, timedelta
from io import BytesIO
from secrets import token_urlsafe, compare_digest
from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, session, url_for
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from models import db
from models.institutional_user import InstitutionalUser
from models.school import School
from models.workshop import WorkshopAccess, WorkshopSlot, WorkshopEnrollment
from services.basic_results import AREAS, COURSES
from services.workshop_catalog import bank, workshop, previews, today_chile, group_recommendations

catalog_bp = Blueprint('catalog', __name__, url_prefix='/talleres')


def school_context():
    if session.get('colegio_logged'):
        user = db.session.get(InstitutionalUser, session.get('colegio_user_id'))
        if not user or not user.is_active or user.school_id != session.get('colegio_school_id'):
            abort(403)
        return user.school_id, user.school_name
    if not session.get('admin_logged'):
        abort(403)
    school_id = request.values.get('school_id', type=int)
    school = db.session.get(School, school_id) if school_id else None
    return (school.id, school.name) if school else (None, '')


def csrf_token():
    if '_workshop_csrf' not in session:
        session['_workshop_csrf'] = token_urlsafe(32)
    return session['_workshop_csrf']


@catalog_bp.before_request
def protect():
    if not session.get('admin_logged') and not session.get('colegio_logged'):
        return redirect(url_for('colegio.login'))
    if session.get('colegio_logged'):
        school_context()
    if request.method == 'POST':
        expected = session.get('_workshop_csrf', '')
        supplied = request.form.get('csrf', '')
        if not expected or not compare_digest(expected, supplied):
            abort(400, 'La sesión del formulario cambió. Recargue la página.')


def access_active(school_id):
    if not school_id:
        return False
    if session.get('colegio_logged'):
        user = db.session.get(InstitutionalUser, session.get('colegio_user_id'))
        return bool(user and user.is_active and user.school_id == school_id)
    return bool(session.get('admin_logged') and InstitutionalUser.query.filter_by(school_id=school_id, is_active=True).first())


def current_results(school_id):
    if not school_id:
        return []
    from routes.colegio import obtener_registros_vigentes_colegio
    return obtener_registros_vigentes_colegio(school_id)


def group_sections(results, course):
    return sorted({r.section or 'SIN PARALELO' for r in results if r.course == course})


def owned_enrollment(identifier):
    enrollment = db.session.get(WorkshopEnrollment, identifier)
    slot = db.session.get(WorkshopSlot, enrollment.slot_id) if enrollment else None
    school_id, name = school_context()
    if not slot or slot.school_id != school_id:
        abort(404)
    return enrollment, slot, name


@catalog_bp.route('/catalogo')
def index():
    school_id, school_name = school_context()
    level = request.args.get('level', 'basica')
    if level not in ('basica', 'media'):
        abort(400)
    course = request.args.get('course', '')
    valid_courses = COURSES if level == 'basica' else ('1° Medio','2° Medio','3° Medio','4° Medio')
    if course and course not in valid_courses:
        course = ''
    areas = [a for a in request.args.getlist('area') if a in AREAS]
    results = current_results(school_id)
    sections = group_sections(results, course)
    section = request.args.get('section', '')
    if section not in sections:
        section = ''
    if not section and len(sections) == 1:
        section = sections[0]
    group = [r for r in results if r.course == course and (not section or (r.section or 'SIN PARALELO') == section)] if course else []
    slot = WorkshopSlot.query.filter_by(school_id=school_id, course=course, section=section).first() if school_id and course and section else None
    active = db.session.get(WorkshopEnrollment, slot.current_enrollment_id) if slot and slot.current_enrollment_id else None
    ready = active is None or today_chile() >= active.available_on
    active_workshop = workshop(active.workshop_id) if active else None
    history = (WorkshopEnrollment.query.join(WorkshopSlot, WorkshopSlot.id == WorkshopEnrollment.slot_id)
               .filter(WorkshopSlot.school_id == school_id).order_by(WorkshopEnrollment.id.desc()).all()) if school_id else []
    for entry in history:
        entry.group_section = db.session.get(WorkshopSlot, entry.slot_id).section
    items = previews(course, areas) if level == 'basica' else []
    # No HTML del banco completo entra en el contexto del catálogo.
    return render_template('talleres/catalog.html', items=items, school_id=school_id, school_name=school_name,
        schools=School.query.order_by(School.name).all() if session.get('admin_logged') and not session.get('colegio_logged') else [],
        courses=valid_courses, course=course, areas=AREAS, selected_areas=areas, sections=sections, section=section, level=level,
        recommendations=group_recommendations(group), active=active,
        active_name=active_workshop['name'] if active_workshop else '', ready=ready,
        entitled=access_active(school_id), can_select=bool(school_id and course in COURSES and section and ready and access_active(school_id)),
        csrf=csrf_token(), history=history, workshop_lookup=workshop, today=today_chile())


@catalog_bp.route('/seleccionar/<identifier>', methods=['POST'])
def select(identifier):
    school_id, _ = school_context()
    item = workshop(identifier)
    if not item:
        abort(404)
    if not access_active(school_id):
        abort(403, 'El acceso a materiales no está vigente.')
    course = request.form.get('course', '')
    section = request.form.get('section', '')
    if item['course'] != course or section not in group_sections(current_results(school_id), course):
        abort(400, 'Seleccione un curso y paralelo vigentes de su establecimiento.')
    try:
        slot = WorkshopSlot.query.filter_by(school_id=school_id, course=course, section=section).with_for_update().first()
        if not slot:
            slot = WorkshopSlot(school_id=school_id, course=course, section=section)
            db.session.add(slot); db.session.flush()
        previous = db.session.get(WorkshopEnrollment, slot.current_enrollment_id) if slot.current_enrollment_id else None
        if previous and today_chile() < previous.available_on:
            abort(409, 'El curso ya tiene un taller activo; puede volver a descargarlo.')
        if previous:
            previous.status = 'finalizado'
        enrollment = WorkshopEnrollment(slot_id=slot.id, workshop_id=identifier, bank_version=bank()['version'],
            started_on=today_chile(), available_on=today_chile() + timedelta(weeks=item['sessions']), sessions=item['sessions'],
            created_by=session.get('colegio_user_id') or session.get('user_id'))
        db.session.add(enrollment); db.session.flush()
        slot.current_enrollment_id = enrollment.id
        db.session.commit()
    except (IntegrityError, StaleDataError):
        db.session.rollback()
        abort(409, 'Otra selección se guardó para este curso. Recargue el catálogo.')
    return redirect(url_for('catalog.download', identifier=enrollment.id, school_id=school_id))


@catalog_bp.route('/material/<int:identifier>')
def download(identifier):
    enrollment, slot, school_name = owned_enrollment(identifier)
    if not access_active(slot.school_id):
        abort(403, 'El acceso a materiales no está vigente.')
    item = workshop(enrollment.workshop_id)
    if not item:
        abort(404)
    # Solo esta ficha; nada del resto del banco se incrusta o se entrega al navegador.
    from services.workshop_pdf import create_workshop_pdf
    content = create_workshop_pdf(item, bank()['intro'], school_name, slot.course, slot.section, enrollment)
    response = send_file(content, as_attachment=True,
        download_name=f"SIOE_Taller_{item['id']}.pdf", mimetype='application/pdf')
    response.headers['Cache-Control'] = 'private, no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@catalog_bp.route('/avance/<int:identifier>', methods=['POST'])
def progress(identifier):
    enrollment, slot, _ = owned_enrollment(identifier)
    if not access_active(slot.school_id):
        abort(403)
    if slot.current_enrollment_id != enrollment.id:
        abort(409)
    count = request.form.get('sessions_done', type=int)
    if count is None or not 0 <= count <= enrollment.sessions:
        abort(400)
    enrollment.sessions_done = count
    enrollment.feedback = request.form.get('feedback', '').strip()[:3000]
    db.session.commit()
    flash('Avance guardado. La fecha de habilitación se mantiene según la duración del taller.', 'success')
    return redirect(url_for('catalog.index', school_id=slot.school_id, course=slot.course, section=slot.section))


@catalog_bp.route('/reemplazo/<int:identifier>', methods=['POST'])
def request_replacement(identifier):
    enrollment, slot, _ = owned_enrollment(identifier)
    if not access_active(slot.school_id) or slot.current_enrollment_id != enrollment.id:
        abort(403)
    reason = request.form.get('reason', '').strip()
    if not 10 <= len(reason) <= 2000:
        abort(400, 'Explique el motivo del reemplazo (10 a 2000 caracteres).')
    enrollment.replacement_reason = reason
    enrollment.replacement_decision = None
    db.session.commit()
    flash('Solicitud de reemplazo registrada para revisión del administrador.', 'success')
    return redirect(url_for('catalog.index', school_id=slot.school_id, course=slot.course, section=slot.section))


@catalog_bp.route('/gestion')
def management():
    if not session.get('admin_logged') or session.get('colegio_logged'):
        abort(403)
    requests = WorkshopEnrollment.query.filter(WorkshopEnrollment.replacement_reason.isnot(None), WorkshopEnrollment.replacement_decision.is_(None)).all()
    return render_template('talleres/management.html', schools=School.query.order_by(School.name).all(),
        requests=requests, csrf=csrf_token(),
        slot_lookup=lambda i: db.session.get(WorkshopSlot,i), school_lookup=lambda i: db.session.get(School,i), workshop_lookup=workshop)


@catalog_bp.route('/gestion/reemplazo/<int:identifier>', methods=['POST'])
def decide_replacement(identifier):
    if not session.get('admin_logged') or session.get('colegio_logged'):
        abort(403)
    enrollment = db.session.get(WorkshopEnrollment, identifier)
    if not enrollment or not enrollment.replacement_reason or enrollment.replacement_decision:
        abort(404)
    slot = WorkshopSlot.query.filter_by(id=enrollment.slot_id).with_for_update().first()
    if slot.current_enrollment_id != enrollment.id:
        abort(409)
    decision = request.form.get('decision')
    if decision not in ('aprobar','rechazar'):
        abort(400)
    enrollment.replacement_decision = decision
    if decision == 'aprobar':
        enrollment.status = 'reemplazado'
        slot.current_enrollment_id = None
    try:
        db.session.commit()
    except StaleDataError:
        db.session.rollback()
        abort(409, 'El taller del grupo cambió. Recargue la gestión de reemplazos.')
    flash('Decisión de reemplazo registrada.', 'success')
    return redirect(url_for('catalog.management'))
