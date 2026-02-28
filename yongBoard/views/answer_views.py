from datetime import datetime
from flask import Blueprint, url_for, request, render_template, g, flash
from werkzeug.utils import redirect
from yongBoard import db
from ..forms import AnswerForm
from yongBoard.models import Question, Answer, User
from .auth_views import login_required

bp = Blueprint("answer", __name__, url_prefix="/answer")


@bp.route("/create/<int:question_id>", methods=("POST",))
@login_required
def create(question_id):
    form = AnswerForm()
    question = Question.query.get_or_404(question_id)
    if form.validate_on_submit():
        content = request.form["content"]
        answer = Answer(content=content, create_date=datetime.now(), user=g.user)
        question.answer_set.append(answer)
        db.session.commit()
        return redirect(
            "{}#answer_{}".format(
                url_for("question.detail", question_id=question_id), answer.id
            )
        )
    return render_template(
        "question/question_detail.html", question=question, form=form
    )


@bp.route("modify/<int:answer_id>", methods=("GET", "POST"))
@login_required
def modify(answer_id):
    answer = Answer.query.get_or_404(answer_id)
    if g.user != answer.user:
        flash("수정권한이 없습니다.")
        return redirect(url_for("question.detail", question_id=answer.question.id))
    if request.method == "POST":
        form = AnswerForm()
        if form.validate_on_submit():
            form.populate_obj(answer)
            answer.modify_date = datetime.now()
            db.session.commit()
            return redirect(
                "{}#answer_{}".format(
                    url_for("question.detail", question_id=answer.question.id),
                    answer.id,
                )
            )
    else:
        form = AnswerForm(obj=answer)
    return render_template("answer/answer_form.html", form=form)


@bp.route("/delete/<int:answer_id>")
@login_required
def delete(answer_id):
    answer = Answer.query.get_or_404(answer_id)
    question_id = answer.question.id
    if g.user != answer.user:
        flash("삭제권한이 없습니다")
    else:
        db.session.delete(answer)
        db.session.commit()
    return redirect(url_for("question.detail", question_id=question_id))


@bp.route("/vote/<int:answer_id>/")
@login_required
def vote(answer_id):
    _answer = Answer.query.get_or_404(answer_id)
    if g.user == _answer.user:
        flash("본인이 작성한 글은 추천할 수가 없습니다.")
    else:
        _answer.voter.append(g.user)
        db.session.commit()
    return redirect(
        "{}#answer_{}".format(
            url_for("question.detail", question_id=_answer.question.id), _answer.id
        )
    )


@bp.route("/list/")
def _list():
    page = request.args.get("page", type=int, default=1)
    kw = request.args.get("kw", type=str, default="")
    question_list = Question.query.order_by(Question.create_date.desc())
    if kw:
        search = "%%{}%%".format(kw)
        sub_query = (
            db.session.query(Answer.question_id, Answer.content, User.username)
            .join(User, Answer.user_id == User.id)
            .subquery()
        )
        question_list = (
            question_list.join(User)
            .outerjoin(sub_query, sub_query.c.question_id == Question.id)
            .filter(
                Question.subject.ilike(search)
                | Question.content.ilike(search)
                | User.username.ilike(search)
                | sub_query.c.content.ilike(search)
                | sub_query.c.username.ilike(search)
            )
            .distinct()
        )
    question_list = question_list.paginate(page=page, per_page=10)
    return render_template(
        "question/question_list.html", question_list=question_list, page=page, kw=kw
    )
