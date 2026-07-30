"use client";

import { useState } from "react";

import { useAssignTraining, useCreateTrainingCourse, useTrainingAssignments, useTrainingCourses } from "@/lib/hooks/use-staff-operations";
import { useStaffList } from "@/lib/hooks/use-staff";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { TRAINING_ASSIGNMENT_STATUS_TONES, formatDate, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function TrainingView() {
  const { data: currentUser } = useCurrentUser();
  const canManageCourses = hasPermission(currentUser, "staff.training.manage");
  const canAssign = hasPermission(currentUser, "staff.training.assign");

  const [error, setError] = useState<string | null>(null);

  const { data: staffPage } = useStaffList({ page: 1, pageSize: 100 });
  const staffOptions = staffPage?.data ?? [];

  const { data: courses } = useTrainingCourses();
  const { data: assignments, isLoading } = useTrainingAssignments();

  const createCourse = useCreateTrainingCourse();
  const assignTraining = useAssignTraining();

  const [courseCode, setCourseCode] = useState("");
  const [courseTitle, setCourseTitle] = useState("");
  const [assignCourseId, setAssignCourseId] = useState("");
  const [assignStaffId, setAssignStaffId] = useState("");

  const courseTitleFor = (id: string) => courses?.find((c) => c.id === id)?.title ?? "Course";
  const staffName = (id: string) =>
    staffOptions.find((s) => s.id === id)?.display_name ?? "Unknown staff";

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader title="Training" description="Training courses and staff assignments." />

      {error && <p className="text-sm text-red-600">{error}</p>}

      <Tabs defaultValue="assignments">
        <TabsList>
          <TabsTrigger value="assignments">Assignments</TabsTrigger>
          <TabsTrigger value="courses">Courses</TabsTrigger>
        </TabsList>

        <TabsContent value="assignments" className="flex flex-col gap-4 pt-4">
          {canAssign && (
            <SectionCard title="Assign training">
              <div className="flex flex-wrap items-end gap-2">
                <Select value={assignCourseId} onValueChange={setAssignCourseId}>
                  <SelectTrigger className="w-48" aria-label="Course">
                    <SelectValue placeholder="Course" />
                  </SelectTrigger>
                  <SelectContent>
                    {(courses ?? []).map((course) => (
                      <SelectItem key={course.id} value={course.id}>
                        {course.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={assignStaffId} onValueChange={setAssignStaffId}>
                  <SelectTrigger className="w-48" aria-label="Staff member">
                    <SelectValue placeholder="Staff member" />
                  </SelectTrigger>
                  <SelectContent>
                    {staffOptions.map((s) => (
                      <SelectItem key={s.id} value={s.id}>
                        {s.display_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  size="sm"
                  disabled={!assignCourseId || !assignStaffId || assignTraining.isPending}
                  onClick={() =>
                    assignTraining.mutate(
                      { course_id: assignCourseId, staff_user_id: assignStaffId },
                      {
                        onError: (err) =>
                          setError(err instanceof ApiError ? err.message : "Could not assign training."),
                      },
                    )
                  }
                >
                  Assign
                </Button>
              </div>
            </SectionCard>
          )}

          <SectionCard title="Assignments">
            <ul className="flex flex-col gap-2 text-sm">
              {isLoading && <li className="text-muted-foreground">Loading…</li>}
              {(assignments ?? []).map((assignment) => (
                <li key={assignment.id} className="flex items-center justify-between gap-2">
                  <span>
                    {staffName(assignment.staff_user_id)} · {courseTitleFor(assignment.course_id)}
                    {assignment.due_at ? ` · due ${formatDate(assignment.due_at)}` : ""}
                  </span>
                  <StatusBadge
                    label={humanize(assignment.status)}
                    tone={TRAINING_ASSIGNMENT_STATUS_TONES[assignment.status]}
                  />
                </li>
              ))}
              {!isLoading && !assignments?.length && (
                <li className="text-muted-foreground">No training assignments yet.</li>
              )}
            </ul>
          </SectionCard>
        </TabsContent>

        <TabsContent value="courses" className="flex flex-col gap-4 pt-4">
          <SectionCard title="Training courses">
            {canManageCourses && (
              <div className="mb-3 flex items-end gap-2">
                <Input
                  placeholder="Code"
                  value={courseCode}
                  onChange={(e) => setCourseCode(e.target.value)}
                  className="w-32"
                />
                <Input
                  placeholder="Course title"
                  value={courseTitle}
                  onChange={(e) => setCourseTitle(e.target.value)}
                  className="w-64"
                />
                <Button
                  size="sm"
                  disabled={!courseCode || !courseTitle || createCourse.isPending}
                  onClick={() =>
                    createCourse.mutate(
                      { code: courseCode, title: courseTitle },
                      {
                        onSuccess: () => {
                          setCourseCode("");
                          setCourseTitle("");
                        },
                        onError: (err) =>
                          setError(err instanceof ApiError ? err.message : "Could not create course."),
                      },
                    )
                  }
                >
                  Add course
                </Button>
              </div>
            )}
            <ul className="flex flex-col gap-2 text-sm">
              {(courses ?? []).map((course) => (
                <li key={course.id} className="flex items-center justify-between gap-2">
                  <span>{course.title}</span>
                  {course.is_mandatory && <StatusBadge label="Mandatory" tone="warning" />}
                </li>
              ))}
              {!courses?.length && <li className="text-muted-foreground">No courses yet.</li>}
            </ul>
          </SectionCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}
