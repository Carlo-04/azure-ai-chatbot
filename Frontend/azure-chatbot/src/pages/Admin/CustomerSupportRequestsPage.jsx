import React, { useState, useEffect } from "react";
import axios from "axios";
import { Accordion, AccordionTab } from "primereact/accordion";
import { Editor } from "primereact/editor";

import { useUser } from "../../contexts/UserContext";
import LoadingSpinner from "../../components/LoadingSpinner";

export default function CustomerSupportRequestsPage() {
  // sample request:{
  //         "request_id": r["id"],
  //         "user_id": r["userId"],
  //         "subject": r["subject"],
  //         "description": r["description"],
  //         "createdAt": r["createdAt"]
  //       }
  const [openRequestsList, setOpenRequestsList] = useState([]); //list of unassigned support requests.
  const [openRequestsLoading, setOpenRequestsLoading] = useState(true);
  const [inProgressRequestsList, setInProgressRequestsList] = useState([]); //list of unassigned support requests.
  const [inProgressRequestsActiveIndex, setInProgressRequestsActiveIndex] =
    useState(null);
  const [inProgressRequestsLoading, setInProgressRequestsLoading] =
    useState(true);
  const [emailDraftText, setEmailDraftText] = useState("");
  const [emailDraftHtml, setEmailDraftHtml] = useState("");

  const [draftingEmail, setDraftingEmail] = useState(false); //toggles the editor to write the email
  const [sendingEmail, setSendingEmail] = useState(false);
  const { user } = useUser();

  ////////////
  // API Functions
  ////////////
  const handleGetOpenRequests = async () => {
    try {
      setOpenRequestsLoading(true);
      const response = await axios.get(
        "https://fa-ict-coueiss-sdc-01-d2g5h9gddrcucygu.swedencentral-01.azurewebsites.net/api/customer_support_list_open_requests",
        {
          params: { user_id: user.id },
        }
      );
      setOpenRequestsList(response.data.open_requests);
      setOpenRequestsLoading(false);
    } catch (error) {
      console.error("Error fetching open requests: ", error);
      alert("Error fetching open requests: ");
    }
  };

  const handleGetInProgressRequests = async () => {
    try {
      setInProgressRequestsLoading(true);
      const response = await axios.get(
        "https://fa-ict-coueiss-sdc-01-d2g5h9gddrcucygu.swedencentral-01.azurewebsites.net/api/customer_support_list_in_progress_requests_by_agent",
        {
          params: { user_id: user.id },
        }
      );
      setInProgressRequestsList(response.data.in_progress_requests);
      setInProgressRequestsLoading(false);
    } catch (error) {
      console.error("Error fetching open requests: ", error);
      alert("Error fetching open requests: ");
    }
  };

  const handleHandleRequest = async (request_id, customer_id, index) => {
    try {
      const response = await axios.post(
        "https://fa-ict-coueiss-sdc-01-d2g5h9gddrcucygu.swedencentral-01.azurewebsites.net/api/customer_support_handle_support_request",
        {
          user_id: user.id,
          request_id: request_id,
          customer_id: customer_id,
        }
      );
      //remove from open requests list and add to in progress list
      const request = openRequestsList[index];
      setOpenRequestsList((prev) =>
        prev.filter((r) => r.request_id !== request.request_id)
      );
      setInProgressRequestsList((prev) => [request, ...prev]);
    } catch (error) {
      if (error.response) {
        if (error.response.status === 409) {
          // Handle conflict when another agent already claimed the request
          alert("This request has already been taken by another agent.");
          // Refresh the open requests list to reflect the current state
          handleGetOpenRequests();
        } else {
          console.error("Error:", error.response.data);
          alert(
            "An error occurred: " +
              (error.response.data.error || "Please try again.")
          );
        }
      } else {
        console.error("Request failed:", error.message);
        alert(
          "Request failed. Please check your network connection and try again."
        );
      }
    }
  };

  const handleCloseRequest = async (request_id, customer_id, index) => {
    try {
      const response = await axios.post(
        "https://fa-ict-coueiss-sdc-01-d2g5h9gddrcucygu.swedencentral-01.azurewebsites.net/api/customer_support_close_support_request",
        {
          user_id: user.id,
          request_id: request_id,
          customer_id: customer_id,
        }
      );
      //remove from ongoing requests list and add to in progress list
      const request = inProgressRequestsList[index];
      setInProgressRequestsList((prev) =>
        prev.filter((r) => r.request_id !== request.request_id)
      );
    } catch (error) {
      if (error.response) {
        console.error("Error:", error.response.data);
        alert(
          "An error occurred: " +
            (error.response.data.error || "Please try again.")
        );
      } else {
        console.error("Request failed:", error.message);
        alert(
          "Request failed. Please check your network connection and try again."
        );
      }
    }
  };

  const handleSendEmail = async (customer_id) => {
    try {
      setSendingEmail(true);
      const response = await axios.post(
        "https://fa-ict-coueiss-sdc-01-d2g5h9gddrcucygu.swedencentral-01.azurewebsites.net/api/customer_support_send_email",
        {
          user_id: user.id,
          recipient_id: customer_id,
          subject: "Dealership Customer Support",
          body_text: emailDraftText,
          body_html: emailDraftHtml,
        }
      );
      setSendingEmail(false);
      setEmailDraftHtml("");
      setEmailDraftText("");
      alert("Email Sent Successfully");
    } catch (error) {
      if (error.response) {
        console.error("Error:", error.response.data);
        alert(
          "An error occurred: " +
            (error.response.data.error || "Please try again.")
        );
      } else {
        console.error("Request failed:", error.message);
        alert(
          "Request failed. Please check your network connection and try again."
        );
      }
    }
  };
  useEffect(() => {
    handleGetOpenRequests();
    handleGetInProgressRequests();
  }, []);

  ///////////
  // Component functions
  ///////////
  const createOpenRequestsTabs = () => {
    return openRequestsList.map((request, i) => {
      return (
        <AccordionTab
          key={i}
          headerTemplate={() => (
            <div className="flex flex-row justify-between items-center w-full">
              <span className="font-semibold text-gray-800">
                {request.subject}
              </span>
              <div className="flex flex-row gap-2">
                <button
                  className="bg-bg-secondary hover:bg-bg-tertiary text-text-primary"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleHandleRequest(request.request_id, request.user_id, i);
                  }}>
                  Handle Request
                </button>
              </div>
            </div>
          )}
          disabled={request.disabled}>
          {request.description}
        </AccordionTab>
      );
    });
  };

  const createAgentRequestsTabs = () => {
    return inProgressRequestsList.map((request, i) => {
      return (
        <AccordionTab
          key={i}
          headerTemplate={() => (
            <div className="flex flex-row justify-between items-center w-full">
              <span className="font-semibold text-gray-800">
                {request.subject}
              </span>
              <div className="flex flex-row gap-2">
                <button
                  className="bg-bg-secondary hover:bg-bg-tertiary text-text-primary"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleCloseRequest(request.request_id, request.user_id, i);
                  }}>
                  Close Request
                </button>
              </div>
            </div>
          )}
          disabled={request.disabled}>
          <div className="flex flex-row justify-between">
            <div className="flex flex-1">{request.description}</div>
            <div className="flex flex-1 flex-col gap-3 justify-center items-center">
              <div>
                <Editor
                  value={emailDraftHtml}
                  onTextChange={(e) => {
                    setEmailDraftHtml(e.htmlValue);
                    setEmailDraftText(e.textValue);
                  }}
                  className="max-h-100 overflow-auto"
                />
              </div>
              <div>
                <button
                  className="bg-bg-secondary hover:bg-bg-tertiary text-text-primary"
                  onClick={() => {
                    handleSendEmail(request.user_id);
                  }}>
                  {sendingEmail && "Sending..."}
                  {!sendingEmail && "Send"}
                </button>
              </div>
            </div>
          </div>
        </AccordionTab>
      );
    });
  };
  return (
    <div>
      <div className="p-4">
        <h1>Your Ongoing Requests</h1>
        <div className="mt-4 rounded-2xl p-4 bg-bg-secondary items-center justify-center">
          {inProgressRequestsList.length === 0 &&
            !inProgressRequestsLoading && (
              <div className="text-text-secondary w-full text-center">
                No requests are assigned to you.
              </div>
            )}
          {inProgressRequestsLoading && <LoadingSpinner />}
          {inProgressRequestsList.length > 0 && !inProgressRequestsLoading && (
            <Accordion
              activeIndex={inProgressRequestsActiveIndex}
              onTabChange={(e) => {
                setInProgressRequestsActiveIndex(e.index);
                setEmailDraftHtml("");
                setEmailDraftText("");
              }}
              onTabClose={() => {
                setInProgressRequestsActiveIndex(null);
                setEmailDraftHtml("");
                setEmailDraftText("");
              }}>
              {createAgentRequestsTabs()}
            </Accordion>
          )}
        </div>
      </div>
      <div className="p-4">
        <h1>Open Support Requests</h1>
        <div className="mt-4 rounded-2xl p-4 bg-bg-secondary  overflow-auto items-center justify-center">
          {openRequestsList.length === 0 && !openRequestsLoading && (
            <div className="h-5 text-text-secondary w-full text-center">
              There are no open requests available.
            </div>
          )}
          {openRequestsLoading && <LoadingSpinner />}
          {openRequestsList.length > 0 && !openRequestsLoading && (
            <Accordion>{createOpenRequestsTabs()}</Accordion>
          )}
        </div>
      </div>
    </div>
  );
}
