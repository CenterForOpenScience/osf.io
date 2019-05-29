<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Dear ${user.fullname},<br>
    <br>
    Thank you for submitting your research plan to the Preregistration Challenge. <br>
    <br>
    Reviewers have made comments on your plan. We require that you address the comments found on ${draft_url} and resubmit.<br>
    <br>
    Each submission must pass this review process in which the statistical methods of the proposed study and its analyses are checked for completeness and adherence to Preregistration Challenge eligibility requirements (https://cos.io/prereg). This review does not assess the substance of the research, or the validity of the research design or statistical methodology. This review has no impact on the independent editorial decisions of any journal.<br>
    <br>
    Prereg Challenge administrators and reviewers review the submitted study design and analysis descriptions, and determine whether all question fields are answered with enough detail to fully pre-specify the design and analysis plan, and follow the eligibility requirements. See https://osf.io/h4ga8/ to learn more about the guidelines that reviewers use when evaluating your submitted plans.<br>
    <br>
    Sincerely,<br>
    <br>
    The team at the Center for Open Science<br>

</tr>
</%def>
