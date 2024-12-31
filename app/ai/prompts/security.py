prompt = """
You are tasked with generating a smart contract audit report. This is strictly a Security audit, and your findings should
only highlight security vulnerabilities.

Please adhere strictly to the following guidelines and don't make mistakes:

The output must match the provided JSON structure exactly, each field has descriptions. You must follow the types provided exactly, and follow the descriptions.

The JSON structure that you must follow is here:


{
  "audit_summary": {
    "project_name": "string | null", // project name that you are able to infer, if possible
  },
  "introduction": "string", // a brief introduction of the smart contract's function
  "scope": "string", // a brief overview of the scope of the smart contract audit
  "findings": {
    "critical": ["string"], // a list of issues that can lead to contract compromise or significant financial losses. Include references to the smart contract code when possible
    "high": ["string"], // a list of severe bugs that may result in major exploits or disruptions. Include references to the smart contract code when possible
    "medium": ["string"], // a list of moderate risks with potential functional or security impacts. Include references to the smart contract code when possible
    "low": ["string"], // a list of minor issues with limited risk or impact. Include references to the smart contract code when possible
    "informational": ["string"], // a list of suggestions for code quality or optimization, with no immediate security risks. Include references to the smart contract code when possible
  },
  "recommendations": ["string"], // a list of high level recommendations to provide the user
  "conclusion": "string" // a summary of your findings
}


Be certain in how you classify each finding. A classification can have 0 to many findings, but do not hallucinate a category.
It's also important that each component of the finding should be as specific as possible, with references to the provided code within the description.
<{code_structured}>

The code to be audited for the Security Audit is found below:

<{prompt}>
"""
